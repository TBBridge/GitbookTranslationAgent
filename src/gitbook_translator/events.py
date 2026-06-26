"""Pipeline event helpers."""

from __future__ import annotations

from gitbook_translator.models import ProgressEvent


def stage_event(stage: str, message: str | None = None) -> ProgressEvent:
    """Create a standard stage progress event."""

    return ProgressEvent(kind="stage", stage=stage, message=message)


__all__ = ["stage_event"]
