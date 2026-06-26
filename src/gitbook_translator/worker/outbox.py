"""Durable progress-event outbox for local workers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gitbook_translator.models import ProgressEvent


_AUTH_HEADER_RE = re.compile(
    r"(?i)(Authorization:\s*(?:Bearer|Basic)\s+)([^\s\"']+)"
)
_COOKIE_HEADER_RE = re.compile(r"(?i)(Cookie:\s*)([^\n\"']+)")
_SECRET_PAIR_RE = re.compile(
    r"(?i)\b(token|api[_-]?key|secret|password|cookie)=([^&\s\"']+)"
)


@dataclass(frozen=True)
class OutboxRecord:
    """One pending progress event with its delivery sequence."""

    sequence: int
    event: ProgressEvent


class Outbox:
    """Append-only JSONL outbox with atomic acknowledgement state."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.state_path = self.path.with_suffix(self.path.suffix + ".state")

    def append(self, event: ProgressEvent) -> int:
        """Sanitize and append an event, returning its assigned sequence."""

        sequence = self.last_sequence + 1
        record = OutboxRecord(sequence=sequence, event=_sanitize_event(event))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(_record_to_json(record), ensure_ascii=False))
            file.write("\n")
        return sequence

    def pending(self) -> list[OutboxRecord]:
        """Return records not yet acknowledged by the control plane."""

        acknowledged = self.acknowledged_sequence
        return [
            record
            for record in self._records()
            if record.sequence > acknowledged
        ]

    def pending_batch(self, max_records: int = 50) -> list[OutboxRecord]:
        """Return a bounded pending batch."""

        if max_records <= 0:
            raise ValueError("max_records must be positive")
        return self.pending()[:max_records]

    def acknowledge(self, sequence: int) -> None:
        """Persist an acknowledgement and compact acknowledged records."""

        if sequence < 0:
            raise ValueError("acknowledged sequence cannot be negative")
        current = self.acknowledged_sequence
        acknowledged = max(current, sequence)
        self._atomic_write_json(self.state_path, {"acknowledged_sequence": acknowledged})
        self.compact()

    def compact(self) -> None:
        """Rewrite the outbox, dropping entries at or below the acked sequence."""

        pending = self.pending()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(
            json.dumps(_record_to_json(record), ensure_ascii=False) + "\n"
            for record in pending
        )
        self._atomic_write_text(self.path, payload)

    @property
    def acknowledged_sequence(self) -> int:
        if not self.state_path.is_file():
            return 0
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        value = data.get("acknowledged_sequence", 0)
        if not isinstance(value, int) or value < 0:
            raise ValueError("invalid outbox state")
        return value

    @property
    def last_sequence(self) -> int:
        sequences = [record.sequence for record in self._records()]
        sequences.append(self.acknowledged_sequence)
        return max(sequences, default=0)

    def _records(self) -> list[OutboxRecord]:
        if not self.path.is_file():
            return []

        records: list[OutboxRecord] = []
        for line_number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                records.append(_record_from_json(payload))
            except Exception as exc:
                raise ValueError(
                    f"invalid outbox record at {self.path}:{line_number}"
                ) from exc
        return records

    def _atomic_write_json(self, path: Path, payload: dict[str, Any]) -> None:
        self._atomic_write_text(path, json.dumps(payload, ensure_ascii=False) + "\n")

    def _atomic_write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)


def _record_to_json(record: OutboxRecord) -> dict[str, Any]:
    return {
        "sequence": record.sequence,
        "event": record.event.model_dump(mode="json", exclude_none=True),
    }


def _record_from_json(payload: dict[str, Any]) -> OutboxRecord:
    sequence = payload.get("sequence")
    if not isinstance(sequence, int) or sequence <= 0:
        raise ValueError("outbox record sequence must be a positive integer")
    event = ProgressEvent.model_validate(payload.get("event"))
    return OutboxRecord(sequence=sequence, event=event)


def _sanitize_event(event: ProgressEvent) -> ProgressEvent:
    data = event.model_dump(mode="json", exclude_none=True)
    return ProgressEvent.model_validate(_redact(data))


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        sanitized = _AUTH_HEADER_RE.sub(r"\1[REDACTED]", value)
        sanitized = _COOKIE_HEADER_RE.sub(r"\1[REDACTED]", sanitized)
        return _SECRET_PAIR_RE.sub(r"\1=[REDACTED]", sanitized)
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _is_secret_key(str(key)):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(item)
        return redacted
    return value


def _is_secret_key(key: str) -> bool:
    return key.lower() in {
        "authorization",
        "cookie",
        "credentials",
        "password",
        "secret",
        "token",
    }


__all__ = ["Outbox", "OutboxRecord"]
