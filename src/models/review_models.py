"""Review-related data models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .glossary_models import Glossary


class IssueSeverity(Enum):
    """Severity level of an issue."""

    BLOCKER = "BLOCKER"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class IssueCategory(Enum):
    """Category of an issue."""

    FORMAT = "format"
    COMPLETENESS = "completeness"
    TERMINOLOGY = "terminology"
    LINKS = "links"
    STYLE = "style"


@dataclass
class IssueLocation:
    """Location of an issue in the document."""

    line: int
    column: Optional[int] = None


@dataclass
class Issue:
    """An issue found during review."""

    severity: IssueSeverity
    category: IssueCategory
    location: IssueLocation
    description: str
    suggestion: Optional[str] = None


@dataclass
class ReviewRequest:
    """Request for translation review."""

    original_content: str
    translated_content: str
    target_language: str
    glossary: Glossary


@dataclass
class ReviewResult:
    """Result of translation review."""

    issues: List[Issue] = field(default_factory=list)
    approved: bool = False
