"""File-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict


@dataclass
class FetchedFile:
    """Represents a file fetched from GitHub."""

    path: str
    content: str
    commit_hash: str
    last_modified: datetime


@dataclass
class FileMetadata:
    """Metadata for tracking file changes."""

    path: str
    commit_hash: str
    last_modified: datetime
    translated_languages: List[str] = field(default_factory=list)
    translations: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass
class DiffResult:
    """Result of diff detection."""

    new_files: List[FetchedFile] = field(default_factory=list)
    modified_files: List[FetchedFile] = field(default_factory=list)
    unchanged_files: List[FetchedFile] = field(default_factory=list)
