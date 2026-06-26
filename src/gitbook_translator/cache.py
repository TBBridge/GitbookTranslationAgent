"""Fingerprint-based translation cache."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


CACHE_VERSION = 1


class CacheModel(BaseModel):
    """Base cache model."""

    model_config = ConfigDict(extra="forbid")


class TranslationFingerprint(CacheModel):
    """Complete fingerprint for one file/language translation result."""

    repository_url: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    source_sha256: str = Field(min_length=1)
    source_commit: str = Field(min_length=1)
    language: str = Field(min_length=1)
    dictionary_sha256: str = Field(min_length=1)
    translation_provider: str = Field(min_length=1)
    translation_model: str = Field(min_length=1)
    review_provider: str = Field(min_length=1)
    review_model: str = Field(min_length=1)
    pipeline_version: str = Field(min_length=1)
    output_path: str = Field(min_length=1)


class CacheEntry(TranslationFingerprint):
    """Persisted successful cache entry."""

    completed_at: str = Field(min_length=1)


class CacheLookup(CacheModel):
    """Cache lookup result."""

    hit: bool
    reason: str
    entry: CacheEntry | None = None


class TranslationCache:
    """Versioned JSON cache stored with atomic replacement."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._entries = self._load_entries()

    def cache_key(self, fingerprint: TranslationFingerprint) -> str:
        """Return the stable key for repository/branch/source/language scope."""

        identity = {
            "repository_url": fingerprint.repository_url,
            "branch": fingerprint.branch,
            "source_path": fingerprint.source_path,
            "language": fingerprint.language,
        }
        canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def get(self, key: str) -> CacheEntry | None:
        """Return a raw cache entry by key without hit validation."""

        return self._entries.get(key)

    def lookup(self, fingerprint: TranslationFingerprint) -> CacheLookup:
        """Return whether an existing entry fully matches the requested fingerprint."""

        key = self.cache_key(fingerprint)
        entry = self._entries.get(key)
        if entry is None:
            return CacheLookup(hit=False, reason="missing")

        if _fingerprint_fields(entry) != fingerprint.model_dump():
            return CacheLookup(hit=False, reason="fingerprint_changed", entry=entry)

        if not Path(entry.output_path).is_file():
            return CacheLookup(hit=False, reason="output_missing", entry=entry)

        return CacheLookup(hit=True, reason="hit", entry=entry)

    def record_success(self, fingerprint: TranslationFingerprint) -> CacheEntry:
        """Record a successful translation and persist the cache atomically."""

        entry = CacheEntry(
            **fingerprint.model_dump(),
            completed_at=datetime.now(UTC).isoformat(),
        )
        self._entries[self.cache_key(fingerprint)] = entry
        self._save()
        return entry

    def _load_entries(self) -> dict[str, CacheEntry]:
        if not self.path.is_file():
            return {}

        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("version") != CACHE_VERSION:
            return {}

        entries: dict[str, CacheEntry] = {}
        for key, raw_entry in data.get("entries", {}).items():
            entries[key] = CacheEntry.model_validate(raw_entry)
        return entries

    def _save(self) -> None:
        payload = {
            "version": CACHE_VERSION,
            "entries": {
                key: entry.model_dump(mode="json")
                for key, entry in sorted(self._entries.items())
            },
        }
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        _atomic_write_text(self.path, serialized + "\n")


def _fingerprint_fields(entry: CacheEntry) -> dict[str, str]:
    data = entry.model_dump()
    data.pop("completed_at", None)
    return data


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


__all__ = [
    "CACHE_VERSION",
    "CacheEntry",
    "CacheLookup",
    "TranslationCache",
    "TranslationFingerprint",
]
