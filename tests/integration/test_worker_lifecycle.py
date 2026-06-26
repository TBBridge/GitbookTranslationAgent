from __future__ import annotations

from pathlib import Path

from gitbook_translator.models import PipelineResult, ProgressEvent, RunStatus
from gitbook_translator.worker.client import WorkerControlPlaneClient
from gitbook_translator.worker.config import parse_worker_config
from gitbook_translator.worker.outbox import Outbox
from gitbook_translator.worker.runner import WorkerRunner


class OneEventPipeline:
    def run(self, job, emit, should_cancel=None):
        emit(ProgressEvent(kind="stage", stage="translate", language=job.languages[0]))
        if should_cancel is not None and should_cancel():
            return PipelineResult(status=RunStatus.CANCELLED)
        return PipelineResult(status=RunStatus.SUCCEEDED)


def test_worker_lifecycle_register_claim_update_and_complete(httpx_mock, tmp_path):
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/register",
        json={"workerId": "w1"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/claim",
        json={
            "job": {
                "jobId": "job-1",
                "leaseId": "lease-1",
                "leaseExpiresAt": "2026-06-26T00:05:00Z",
                "config": {
                    "schemaVersion": 1,
                    "repoUrl": "https://github.com/acme/docs",
                    "branch": "main",
                    "targetPaths": ["docs/**/*.md"],
                    "languages": ["en"],
                    "dictionarySet": "default",
                    "outputRoot": "default",
                    "translationProvider": "ollama-local",
                },
            }
        },
    )
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/jobs/job-1/updates",
        json={"acknowledgedSequence": 1},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://control.test/api/worker/v1/jobs/job-1/cancellation?leaseId=lease-1",
        json={"cancelled": False},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://control.test/api/worker/v1/jobs/job-1/cancellation?leaseId=lease-1",
        json={"cancelled": False},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://control.test/api/worker/v1/jobs/job-1/cancellation?leaseId=lease-1",
        json={"cancelled": False},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://control.test/api/worker/v1/jobs/job-1/complete",
        json={"accepted": True, "acknowledgedSequence": 1},
    )

    result = WorkerRunner(
        client=WorkerControlPlaneClient(
            server_url="https://control.test",
            token="worker-secret",
        ),
        pipeline=OneEventPipeline(),
        config=worker_config(tmp_path),
        outbox=Outbox(tmp_path / "outbox.jsonl"),
    ).run_once()

    assert result.status == RunStatus.SUCCEEDED
    request_paths = [request.url.path for request in httpx_mock.get_requests()]
    assert request_paths == [
        "/api/worker/v1/register",
        "/api/worker/v1/claim",
        "/api/worker/v1/jobs/job-1/updates",
        "/api/worker/v1/jobs/job-1/cancellation",
        "/api/worker/v1/jobs/job-1/cancellation",
        "/api/worker/v1/jobs/job-1/cancellation",
        "/api/worker/v1/jobs/job-1/complete",
    ]


def worker_config(tmp_path: Path):
    (tmp_path / "dicts").mkdir()
    (tmp_path / "dicts" / "dictionary_en.json").write_text(
        '{"翻訳":"Translation"}',
        encoding="utf-8",
    )
    return parse_worker_config(
        {
            "server_url": "https://control.test",
            "worker_name": "test-worker",
            "dictionaries": {"default": str(tmp_path / "dicts")},
            "output_roots": {"default": str(tmp_path / "output")},
            "providers": [
                {
                    "name": "ollama-local",
                    "provider": "ollama",
                    "model": "qwen3",
                    "roles": ["translate"],
                }
            ],
        },
        base_dir=tmp_path,
    )
