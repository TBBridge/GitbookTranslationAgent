"""Data models and interfaces for GitBook Translator."""

from .config import CLIConfig
from .file_models import FetchedFile, FileMetadata, DiffResult
from .markdown_models import (
    Segment,
    SegmentType,
    SegmentMetadata,
    ParsedMarkdown,
    StructureInfo,
)
from .glossary_models import Glossary
from .translation_models import TranslationRequest, TranslationResult
from .review_models import (
    Issue,
    IssueSeverity,
    IssueCategory,
    IssueLocation,
    ReviewRequest,
    ReviewResult,
)
from .agent_models import AgentState, ToolResult
from .log_models import LogContext, ProcessingSummary

__all__ = [
    "CLIConfig",
    "FetchedFile",
    "FileMetadata",
    "DiffResult",
    "Segment",
    "SegmentType",
    "SegmentMetadata",
    "ParsedMarkdown",
    "StructureInfo",
    "Glossary",
    "TranslationRequest",
    "TranslationResult",
    "Issue",
    "IssueSeverity",
    "IssueCategory",
    "IssueLocation",
    "ReviewRequest",
    "ReviewResult",
    "AgentState",
    "ToolResult",
    "LogContext",
    "ProcessingSummary",
]
