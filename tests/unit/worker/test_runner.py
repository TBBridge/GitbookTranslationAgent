from __future__ import annotations

from pathlib import Path

from gitbook_translator.models import PipelineResult, ProgressEvent, RunStatus
from gitbook_translator.worker.config import parse_worker_config
from gitbook_translator.worker.models import (
    CancellationState,
    ClaimResponse,
    ClaimedJob,
    CompleteResponse,
    HeartbeatResponse,
    RegisterResponse,
    RenewResponse,
    UpdateAck,
    WorkerJobConfig,
)
from gitbook_translator.worker.outbox import Outbox
from gitbook_translator.worker.runner import WorkerRunner


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeClient:
    def __init__(self, claim_result: ClaimResponse) -> None:
        self.claim_result = claim_result
        self.renew_calls = 0
        self.complete_calls = 0
        self.acknowledged_sequence = 0
        self.cancel_after_sequence: int | None = None
        self.lose_lease_on_renew = False

    def register(self, capabilities):
        return RegisterResponse(worker_id="w1")

    def heartbeat(self, worker_id, capabilities):
        return HeartbeatResponse(accepted=True)

    def claim(self, *, worker_id, capabilities):
        return self.claim_result

    def renew(self, *, job_id, lease_id):
        self.renew_calls += 1
        return RenewResponse(accepted=not self.lose_lease_on_renew)

    def send_updates(self, *, job_id, lease_id, updates, first_sequence):
        self.acknowledged_sequence = first_sequence + len(updates) - 1
        return UpdateAck(acknowledged_sequence=self.acknowledged_sequence)

    def cancellation_state(self, *, job_id, lease_id):
        return CancellationState(
            cancelled=(
                self.cancel_after_sequence is not None
                and self.acknowledged_sequence >= self.cancel_after_sequence
            )
        )

    def complete(self, *, job_id, lease_id, result, last_sequence=None):
        self.complete_calls += 1
        return CompleteResponse(
            accepted=True,
            acknowledged_sequence=last_sequence,
        )

    def cancel_after_progress(self, sequence: int) -> None:
        self.cancel_after_sequence = sequence


class FakePipeline:
    def __init__(self, clock: FakeClock | None = None, advance_seconds: float = 0) -> None:
        self.clock = clock
        self.advance_seconds = advance_seconds
        self.languages_started: list[str] = []
        self.last_job = None

    def run(self, job, emit, should_cancel=None):
        self.last_job = job
        should_cancel = should_cancel or (lambda: False)
        for language in job.languages:
            if should_cancel():
                return PipelineResult(status=RunStatus.CANCELLED)
            self.languages_started.append(language)
            for step in range(3):
                if self.clock is not None:
                    self.clock.advance(self.advance_seconds)
                emit(
                    ProgressEvent(
                        kind="stage",
                        stage=f"translate-{step}",
                        language=language,
                    )
                )
        return PipelineResult(status=RunStatus.SUCCEEDED)


def test_runner_renews_lease_during_long_job(tmp_path):
    clock = FakeClock()
    fake_pipeline = FakePipeline(clock=clock, advance_seconds=15)
    fake_client = FakeClient(claim_result=claim_response(languages=["en"]))
    runner = WorkerRunner(
        client=fake_client,
        pipeline=fake_pipeline,
        config=worker_config(tmp_path, lease_renewal_seconds=10),
        outbox=Outbox(tmp_path / "outbox.jsonl"),
        clock=clock,
        sleeper=lambda _: None,
    )

    runner.run_once()

    assert fake_client.renew_calls >= 2


def test_cancel_request_stops_between_languages(tmp_path):
    fake_client = FakeClient(claim_result=claim_response(languages=["en", "zh-CN"]))
    fake_client.cancel_after_progress(sequence=3)
    fake_pipeline = FakePipeline()
    runner = WorkerRunner(
        client=fake_client,
        pipeline=fake_pipeline,
        config=worker_config(tmp_path),
        outbox=Outbox(tmp_path / "outbox.jsonl"),
        clock=FakeClock(),
        sleeper=lambda _: None,
    )

    result = runner.run_once()

    assert result.status == RunStatus.CANCELLED
    assert fake_pipeline.languages_started == ["en"]


def test_runner_maps_claimed_names_to_local_paths_and_providers(tmp_path):
    fake_pipeline = FakePipeline()
    runner = WorkerRunner(
        client=FakeClient(claim_result=claim_response(languages=["en"])),
        pipeline=fake_pipeline,
        config=worker_config(tmp_path),
        outbox=Outbox(tmp_path / "outbox.jsonl"),
        clock=FakeClock(),
        sleeper=lambda _: None,
    )

    runner.run_once()

    assert fake_pipeline.last_job.dictionary_path == (tmp_path / "dicts").resolve()
    assert fake_pipeline.last_job.output_root == (tmp_path / "output").resolve()
    assert fake_pipeline.last_job.translation_provider.provider == "ollama"
    assert fake_pipeline.last_job.translation_provider.model == "qwen3"


def test_lost_lease_skips_completion_until_next_boundary(tmp_path):
    fake_client = FakeClient(claim_result=claim_response(languages=["en"]))
    fake_client.lose_lease_on_renew = True
    fake_pipeline = FakePipeline(clock=FakeClock(), advance_seconds=20)
    runner = WorkerRunner(
        client=fake_client,
        pipeline=fake_pipeline,
        config=worker_config(tmp_path, lease_renewal_seconds=10),
        outbox=Outbox(tmp_path / "outbox.jsonl"),
        clock=fake_pipeline.clock,
        sleeper=lambda _: None,
    )

    result = runner.run_once()

    assert result.status == RunStatus.CANCELLED
    assert fake_client.complete_calls == 0


def worker_config(tmp_path: Path, **overrides):
    (tmp_path / "dicts").mkdir()
    (tmp_path / "dicts" / "dictionary_en.json").write_text(
        '{"翻訳":"Translation"}',
        encoding="utf-8",
    )
    data = {
        "server_url": "https://control.test",
        "worker_name": "test-worker",
        "lease_renewal_seconds": 15,
        "dictionaries": {"default": str(tmp_path / "dicts")},
        "output_roots": {"default": str(tmp_path / "output")},
        "providers": [
            {
                "name": "ollama-local",
                "provider": "ollama",
                "model": "qwen3",
                "base_url": "http://127.0.0.1:11434",
                "roles": ["translate"],
            }
        ],
    }
    data.update(overrides)
    return parse_worker_config(data, base_dir=tmp_path)


def claim_response(languages: list[str]) -> ClaimResponse:
    return ClaimResponse(
        job=ClaimedJob(
            job_id="job-1",
            lease_id="lease-1",
            lease_expires_at="2026-06-26T00:05:00Z",
            config=WorkerJobConfig(
                repo_url="https://github.com/acme/docs",
                branch="main",
                target_paths=["docs/**/*.md"],
                languages=languages,
                dictionary_set="default",
                output_root="default",
                translation_provider="ollama-local",
            ),
        )
    )
