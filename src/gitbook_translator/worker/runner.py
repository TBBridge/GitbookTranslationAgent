"""Local worker polling, lease, cancellation, and pipeline lifecycle."""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from gitbook_translator.config import normalize_repository_url, validate_branch
from gitbook_translator.models import (
    PipelineResult,
    ProgressEvent,
    ProviderSpec,
    RunStatus,
    TranslationIssue,
    TranslationJob,
)
from gitbook_translator.worker.client import WorkerControlPlaneClient
from gitbook_translator.worker.models import ClaimedJob, WorkerConfig, WorkerJobConfig
from gitbook_translator.worker.outbox import Outbox


Clock = Callable[[], float]
Sleeper = Callable[[float], None]


class PipelineLike(Protocol):
    def run(
        self,
        job: TranslationJob,
        emit: Callable[[ProgressEvent], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> PipelineResult:
        """Run a translation job."""


@dataclass
class _LeaseState:
    job_id: str
    lease_id: str
    last_renewed_at: float
    lost: bool = False
    cancel_requested: bool = False


class WorkerRunner:
    """Poll one control plane and execute claimed jobs locally."""

    def __init__(
        self,
        *,
        client: WorkerControlPlaneClient,
        pipeline: PipelineLike | Callable[[TranslationJob], PipelineLike],
        config: WorkerConfig,
        outbox: Outbox,
        clock: Any | None = None,
        sleeper: Sleeper = time.sleep,
    ) -> None:
        self.client = client
        self.pipeline = pipeline
        self.config = config
        self.outbox = outbox
        self.clock = clock
        self.sleeper = sleeper
        self.worker_id: str | None = None
        self.last_heartbeat_at: float | None = None

    def run_once(self) -> PipelineResult:
        """Perform one register/heartbeat, claim, execute, and report cycle."""

        self._ensure_registered_or_heartbeat()
        claim = self.client.claim(
            worker_id=self._require_worker_id(),
            capabilities=self.config.capabilities,
        )
        if claim.job is None:
            return PipelineResult(status=RunStatus.SUCCEEDED)
        return self._run_claimed_job(claim.job)

    def run_forever(self) -> None:
        """Continuously poll the control plane."""

        while True:
            self.run_once()
            self.sleeper(self.config.poll_interval_seconds)

    def _ensure_registered_or_heartbeat(self) -> None:
        now = self._now()
        if self.worker_id is None:
            response = self.client.register(self.config.capabilities)
            self.worker_id = response.worker_id
            self.last_heartbeat_at = now
            return

        if (
            self.last_heartbeat_at is None
            or now - self.last_heartbeat_at >= self.config.heartbeat_interval_seconds
        ):
            self.client.heartbeat(self.worker_id, self.config.capabilities)
            self.last_heartbeat_at = now

    def _run_claimed_job(self, claimed: ClaimedJob) -> PipelineResult:
        lease = _LeaseState(
            job_id=claimed.job_id,
            lease_id=claimed.lease_id,
            last_renewed_at=self._now(),
        )
        job = self._to_translation_job(claimed.config)

        def emit(event: ProgressEvent) -> None:
            if lease.lost:
                return
            self.outbox.append(event)
            self._flush_outbox(lease)
            self._renew_if_due(lease)
            self._refresh_cancellation(lease)

        def should_cancel() -> bool:
            if lease.lost:
                return True
            self._renew_if_due(lease)
            self._refresh_cancellation(lease)
            return lease.lost or lease.cancel_requested

        try:
            result = self._invoke_pipeline(job, emit, should_cancel)
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            result = PipelineResult(
                status=RunStatus.FAILED,
                issues=[
                    TranslationIssue(
                        code="worker_pipeline_failed",
                        message=str(exc),
                        stage="worker",
                        retriable=True,
                    )
                ],
            )

        if lease.lost:
            return _cancelled_result(result)

        self._flush_outbox(lease)
        if self._refresh_cancellation(lease):
            result = _cancelled_result(result)

        if not lease.lost:
            response = self.client.complete(
                job_id=lease.job_id,
                lease_id=lease.lease_id,
                result=result,
                last_sequence=self.outbox.last_sequence,
            )
            if response.acknowledged_sequence is not None:
                self.outbox.acknowledge(response.acknowledged_sequence)

        return result

    def _invoke_pipeline(
        self,
        job: TranslationJob,
        emit: Callable[[ProgressEvent], None],
        should_cancel: Callable[[], bool],
    ) -> PipelineResult:
        pipeline = self._pipeline_for(job)
        parameters = inspect.signature(pipeline.run).parameters
        kwargs: dict[str, Any] = {"emit": emit}
        if "should_cancel" in parameters:
            kwargs["should_cancel"] = should_cancel
        return pipeline.run(job, **kwargs)

    def _pipeline_for(self, job: TranslationJob) -> PipelineLike:
        if hasattr(self.pipeline, "run"):
            return self.pipeline  # type: ignore[return-value]
        return self.pipeline(job)  # type: ignore[operator]

    def _flush_outbox(self, lease: _LeaseState) -> None:
        while True:
            batch = self.outbox.pending_batch()
            if not batch:
                return
            ack = self.client.send_updates(
                job_id=lease.job_id,
                lease_id=lease.lease_id,
                updates=[record.event for record in batch],
                first_sequence=batch[0].sequence,
            )
            if ack.acknowledged_sequence < batch[0].sequence:
                return
            self.outbox.acknowledge(ack.acknowledged_sequence)

    def _renew_if_due(self, lease: _LeaseState) -> None:
        if lease.lost:
            return
        now = self._now()
        if now - lease.last_renewed_at < self.config.lease_renewal_seconds:
            return
        response = self.client.renew(job_id=lease.job_id, lease_id=lease.lease_id)
        if response.accepted:
            lease.last_renewed_at = now
        else:
            lease.lost = True
            lease.cancel_requested = True

    def _refresh_cancellation(self, lease: _LeaseState) -> bool:
        if lease.lost:
            return True
        state = self.client.cancellation_state(
            job_id=lease.job_id,
            lease_id=lease.lease_id,
        )
        lease.cancel_requested = lease.cancel_requested or state.cancelled
        return lease.cancel_requested

    def _to_translation_job(self, config: WorkerJobConfig) -> TranslationJob:
        dictionary_set = self.config.dictionary_sets.get(config.dictionary_set)
        if dictionary_set is None:
            raise ValueError(f"unknown dictionary set: {config.dictionary_set}")
        try:
            output_root = self.config.output_roots[config.output_root]
        except KeyError as exc:
            raise ValueError(f"unknown output root: {config.output_root}") from exc

        translation_provider = self._provider_spec(config.translation_provider)
        review_provider = (
            self._provider_spec(config.review_provider)
            if config.review_provider is not None
            else None
        )
        return TranslationJob(
            repo_url=normalize_repository_url(config.repo_url),
            branch=validate_branch(config.branch),
            target_paths=config.target_paths,
            languages=config.languages,
            dictionary_path=dictionary_set.path,
            output_root=output_root,
            translation_provider=translation_provider,
            review_provider=review_provider,
        )

    def _provider_spec(self, name: str) -> ProviderSpec:
        for provider in self.config.providers:
            if provider.name == name:
                return ProviderSpec(
                    provider=provider.provider,
                    model=provider.model,
                    base_url=provider.base_url,
                )
        raise ValueError(f"unknown provider: {name}")

    def _require_worker_id(self) -> str:
        if self.worker_id is None:
            raise RuntimeError("worker is not registered")
        return self.worker_id

    def _now(self) -> float:
        if self.clock is None:
            return time.monotonic()
        if hasattr(self.clock, "monotonic"):
            return float(self.clock.monotonic())
        if callable(self.clock):
            return float(self.clock())
        raise TypeError("clock must be callable or expose monotonic()")


def _cancelled_result(result: PipelineResult) -> PipelineResult:
    return PipelineResult(
        status=RunStatus.CANCELLED,
        results=result.results,
        issues=result.issues,
    )


__all__ = ["WorkerRunner"]
