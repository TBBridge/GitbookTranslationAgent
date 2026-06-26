"""Authenticated HTTP client for the worker control-plane contract."""

from __future__ import annotations

import uuid
from typing import Any, TypeVar
from urllib.parse import quote, urlparse

import httpx
from pydantic import ValidationError

from gitbook_translator.models import PipelineResult, ProgressEvent
from gitbook_translator.worker.models import (
    CancellationState,
    ClaimResponse,
    CompleteResponse,
    HeartbeatResponse,
    RegisterResponse,
    RenewResponse,
    UpdateAck,
    WorkerCapabilities,
    WorkerModel,
)


_ResponseT = TypeVar("_ResponseT", bound=WorkerModel)


class ControlPlaneError(RuntimeError):
    """Raised when the worker control plane rejects or cannot parse a request."""


class WorkerControlPlaneClient:
    """Small synchronous client for `/api/worker/v1` endpoints."""

    def __init__(
        self,
        *,
        server_url: str,
        token: str,
        timeout_seconds: float = 30.0,
        worker_version: str = "gitbook-translator/0.1.0",
    ) -> None:
        self.server_url = _validate_server_url(server_url)
        self.token = _validate_token(token)
        self.timeout_seconds = timeout_seconds
        self.worker_version = worker_version

    def register(self, capabilities: WorkerCapabilities) -> RegisterResponse:
        """Register this worker and publish its safe capability payload."""

        return self._post(
            "/register",
            {
                "schemaVersion": 1,
                "capabilities": _dump_worker_model(capabilities),
            },
            RegisterResponse,
            idempotency_key=True,
        )

    def heartbeat(self, worker_id: str, capabilities: WorkerCapabilities) -> HeartbeatResponse:
        """Send a lightweight liveness and capabilities refresh."""

        return self._post(
            "/heartbeat",
            {
                "schemaVersion": 1,
                "workerId": worker_id,
                "capabilities": _dump_worker_model(capabilities),
            },
            HeartbeatResponse,
            idempotency_key=True,
        )

    def claim(
        self,
        *,
        worker_id: str,
        capabilities: WorkerCapabilities,
    ) -> ClaimResponse:
        """Claim at most one queued job for exclusive local execution."""

        return self._post(
            "/claim",
            {
                "schemaVersion": 1,
                "workerId": worker_id,
                "capabilities": _dump_worker_model(capabilities),
            },
            ClaimResponse,
            idempotency_key=True,
        )

    def renew(self, *, job_id: str, lease_id: str) -> RenewResponse:
        """Renew a job lease owned by this worker."""

        return self._post(
            f"/jobs/{_path_id(job_id)}/renew",
            {
                "schemaVersion": 1,
                "leaseId": lease_id,
            },
            RenewResponse,
            idempotency_key=True,
        )

    def send_updates(
        self,
        *,
        job_id: str,
        lease_id: str,
        updates: list[ProgressEvent],
        first_sequence: int,
    ) -> UpdateAck:
        """Deliver a batch of progress updates and return the last acknowledged sequence."""

        return self._post(
            f"/jobs/{_path_id(job_id)}/updates",
            {
                "schemaVersion": 1,
                "leaseId": lease_id,
                "firstSequence": first_sequence,
                "updates": [
                    event.model_dump(mode="json", exclude_none=True)
                    for event in updates
                ],
            },
            UpdateAck,
            idempotency_key=True,
        )

    def cancellation_state(
        self,
        *,
        job_id: str,
        lease_id: str,
    ) -> CancellationState:
        """Read whether the control plane has requested cancellation."""

        return self._get(
            f"/jobs/{_path_id(job_id)}/cancellation",
            CancellationState,
            params={"leaseId": lease_id},
        )

    def complete(
        self,
        *,
        job_id: str,
        lease_id: str,
        result: PipelineResult,
        last_sequence: int | None = None,
    ) -> CompleteResponse:
        """Report final pipeline completion for an owned lease."""

        return self._post(
            f"/jobs/{_path_id(job_id)}/complete",
            {
                "schemaVersion": 1,
                "leaseId": lease_id,
                "lastSequence": last_sequence,
                "result": result.model_dump(mode="json", exclude_none=True),
            },
            CompleteResponse,
            idempotency_key=True,
        )

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        response_model: type[_ResponseT],
        *,
        idempotency_key: bool = False,
    ) -> _ResponseT:
        headers = self._headers(idempotency_key=idempotency_key)
        response = httpx.post(
            self._url(path),
            json=payload,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        return self._parse_response(response, response_model)

    def _get(
        self,
        path: str,
        response_model: type[_ResponseT],
        *,
        params: dict[str, str],
    ) -> _ResponseT:
        response = httpx.get(
            self._url(path),
            params=params,
            headers=self._headers(idempotency_key=False),
            timeout=self.timeout_seconds,
        )
        return self._parse_response(response, response_model)

    def _headers(self, *, idempotency_key: bool) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Worker-Version": self.worker_version,
        }
        if idempotency_key:
            headers["Idempotency-Key"] = str(uuid.uuid4())
        return headers

    def _url(self, path: str) -> str:
        return f"{self.server_url}/api/worker/v1{path}"

    def _parse_response(
        self,
        response: httpx.Response,
        response_model: type[_ResponseT],
    ) -> _ResponseT:
        if response.status_code >= 400:
            raise ControlPlaneError(_failure_message(response))
        if response.status_code == 204:
            return response_model.model_validate({})
        try:
            payload = response.json()
        except ValueError as exc:
            raise ControlPlaneError("control-plane response was not valid JSON") from exc
        try:
            return response_model.model_validate(payload)
        except ValidationError as exc:
            raise ControlPlaneError(f"invalid control-plane response: {exc}") from exc


def _dump_worker_model(model: WorkerModel) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


def _failure_message(response: httpx.Response) -> str:
    if response.status_code in {401, 403}:
        return f"control-plane authentication failed with status {response.status_code}"

    body = response.text.strip()
    if body:
        return f"control-plane request failed with status {response.status_code}: {body[:500]}"
    return f"control-plane request failed with status {response.status_code}"


def _validate_server_url(value: str) -> str:
    server_url = value.strip().rstrip("/")
    parsed = urlparse(server_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("server_url must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("server_url must not include credentials")
    return server_url


def _validate_token(value: str) -> str:
    token = value.strip()
    if not token:
        raise ValueError("worker token is required")
    return token


def _path_id(value: str) -> str:
    if not value:
        raise ValueError("path id is required")
    return quote(value, safe="")


__all__ = ["ControlPlaneError", "WorkerControlPlaneClient"]
