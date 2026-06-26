from __future__ import annotations

import json
from pathlib import Path

import pytest

from gitbook_translator.models import PipelineResult, ProgressEvent, RunStatus
from gitbook_translator.worker.client import (
    ControlPlaneError,
    WorkerControlPlaneClient,
)
from gitbook_translator.worker.models import (
    DictionarySetCapability,
    ProviderCapability,
    WorkerCapabilities,
)


FIXTURES = Path(__file__).parents[2] / "fixtures" / "worker_contract"

CAPABILITIES = WorkerCapabilities(
    worker_name="test-worker",
    dictionary_sets={"default": DictionarySetCapability(languages=["en"])},
    output_roots=["default"],
    providers=[
        ProviderCapability(
            name="ollama-local",
            provider="ollama",
            model="qwen3",
            roles=["translate"],
        )
    ],
)


@pytest.fixture
def worker_client():
    return WorkerControlPlaneClient(
        server_url="https://control.test",
        token="worker-secret",
        timeout_seconds=3,
        worker_version="test-version",
    )


def json_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_register_sends_bearer_token(httpx_mock, worker_client):
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/register",
        json={"workerId": "w1"},
    )

    worker_client.register(CAPABILITIES)

    request = httpx_mock.get_request()
    assert request.headers["Authorization"] == "Bearer worker-secret"
    assert request.headers["X-Worker-Version"] == "test-version"
    assert request.headers["Idempotency-Key"]


def test_register_sends_capabilities_without_paths_or_token(httpx_mock, worker_client):
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/register",
        json=json_fixture("register-success.json"),
    )

    worker_client.register(CAPABILITIES)

    payload = json.loads(httpx_mock.get_request().content)
    serialized = repr(payload)
    assert payload["capabilities"]["dictionarySets"]["default"]["languages"] == ["en"]
    assert "worker-secret" not in serialized
    assert "/Users/" not in serialized


def test_claim_parses_versioned_job(httpx_mock, worker_client):
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/claim",
        json=json_fixture("claim-success.json"),
    )

    claim = worker_client.claim(worker_id="w1", capabilities=CAPABILITIES)

    assert claim.job is not None
    assert claim.job.config.schema_version == 1
    assert claim.job.config.translation_provider == "ollama-local"


def test_claim_204_returns_no_job(httpx_mock, worker_client):
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/claim",
        status_code=204,
    )

    claim = worker_client.claim(worker_id="w1", capabilities=CAPABILITIES)

    assert claim.job is None


def test_complete_posts_versioned_result(httpx_mock, worker_client):
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/jobs/job-1/complete",
        json=json_fixture("complete-success.json"),
    )

    response = worker_client.complete(
        job_id="job-1",
        lease_id="lease-1",
        result=PipelineResult(status=RunStatus.SUCCEEDED),
        last_sequence=7,
    )

    payload = json.loads(httpx_mock.get_request().content)
    assert payload["schemaVersion"] == 1
    assert payload["leaseId"] == "lease-1"
    assert payload["result"]["status"] == "succeeded"
    assert response.acknowledged_sequence == 7


def test_send_updates_uses_aliases_and_acknowledgement(httpx_mock, worker_client):
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/jobs/job-1/updates",
        json={"acknowledgedSequence": 2},
    )

    ack = worker_client.send_updates(
        job_id="job-1",
        lease_id="lease-1",
        updates=[
            ProgressEvent(
                kind="stage",
                stage="translate",
                message="working",
            )
        ],
        first_sequence=2,
    )

    payload = json.loads(httpx_mock.get_request().content)
    assert payload["leaseId"] == "lease-1"
    assert payload["firstSequence"] == 2
    assert ack.acknowledged_sequence == 2


def test_authentication_error_redacts_response_body(httpx_mock, worker_client):
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/register",
        status_code=401,
        text="secret-token-body",
    )

    with pytest.raises(ControlPlaneError) as exc_info:
        worker_client.register(CAPABILITIES)

    assert "secret-token-body" not in str(exc_info.value)
    assert "401" in str(exc_info.value)
