"""Logging-related data models."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class LogContext:
    """Context information for logging."""

    file: Optional[str] = None
    language: Optional[str] = None
    operation: Optional[str] = None


@dataclass
class ProcessingSummary:
    """Summary of processing results."""

    files_processed: int
    translations_created: int
    errors: int
    warnings: int
    duration: float
