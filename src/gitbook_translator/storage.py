"""Atomic output storage helpers."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from gitbook_translator.cache import TranslationCache, TranslationFingerprint


def atomic_write_text(path: str | Path, content: str) -> None:
    """Write text to a temporary sibling and atomically replace the target."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.{uuid4().hex}.tmp"
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def save_output_and_record(
    path: str | Path,
    content: str,
    cache: TranslationCache,
    fingerprint: TranslationFingerprint,
) -> None:
    """Save output first; only then record the successful cache fingerprint."""

    atomic_write_text(path, content)
    cache.record_success(fingerprint)


__all__ = ["atomic_write_text", "save_output_and_record"]
