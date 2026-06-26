from __future__ import annotations

from gitbook_translator.models import ProgressEvent
from gitbook_translator.worker.outbox import Outbox


def progress_event(message: str = "working") -> ProgressEvent:
    return ProgressEvent(kind="stage", stage="translate", message=message)


def test_unsent_events_survive_restart(tmp_path):
    path = tmp_path / "outbox.jsonl"
    sequence = Outbox(path).append(progress_event())

    pending = Outbox(path).pending()

    assert sequence == 1
    assert pending[0].sequence == 1
    assert pending[0].event.stage == "translate"


def test_acknowledge_compacts_sent_events(tmp_path):
    path = tmp_path / "outbox.jsonl"
    outbox = Outbox(path)
    outbox.append(progress_event("one"))
    outbox.append(progress_event("two"))

    outbox.acknowledge(1)

    pending = Outbox(path).pending()
    assert [record.sequence for record in pending] == [2]
    assert "one" not in path.read_text(encoding="utf-8")


def test_outbox_redacts_secrets(tmp_path):
    outbox = Outbox(tmp_path / "outbox.jsonl")

    outbox.append(progress_event("Authorization: Bearer abc123"))

    persisted = outbox.path.read_text(encoding="utf-8")
    assert "abc123" not in persisted
    assert "[REDACTED]" in persisted


def test_outbox_sequence_continues_after_restart(tmp_path):
    path = tmp_path / "outbox.jsonl"
    Outbox(path).append(progress_event())

    sequence = Outbox(path).append(progress_event())

    assert sequence == 2
