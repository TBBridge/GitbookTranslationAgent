"""Language-specific dictionary loading utilities."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DictionaryNotFoundError(FileNotFoundError):
    """Raised when a language-specific dictionary file is not found."""


@dataclass(frozen=True)
class LoadedDictionary:
    """Loaded flat dictionary terms and their canonical content hash."""

    terms: dict[str, str]
    sha256: str


def dictionary_filename(language: str) -> str:
    """Return the normalized filename for a language-specific dictionary."""

    return f"dictionary_{language.lower()}.json"


def load_dictionary(directory: str | Path, language: str) -> LoadedDictionary:
    """Load a strict flat dictionary for ``language`` from ``directory``."""

    path = Path(directory) / dictionary_filename(language)
    if not path.is_file():
        raise DictionaryNotFoundError(f"Dictionary not found: {path}")

    raw_terms = json.loads(path.read_text(encoding="utf-8"))
    terms = _validate_terms(raw_terms, path)
    canonical = json.dumps(
        terms,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return LoadedDictionary(terms=terms, sha256=digest)


def _validate_terms(raw_terms: Any, path: Path) -> dict[str, str]:
    if not isinstance(raw_terms, dict):
        raise ValueError(f"Dictionary must be a JSON object: {path}")

    terms: dict[str, str] = {}
    for key, value in raw_terms.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"Dictionary keys must be non-empty strings: {path}")
        if not isinstance(value, str) or not value:
            raise ValueError(f"Dictionary values must be non-empty strings: {path}")
        terms[key] = value

    return terms


__all__ = [
    "DictionaryNotFoundError",
    "LoadedDictionary",
    "dictionary_filename",
    "load_dictionary",
]
