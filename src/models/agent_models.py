"""Agent-related data models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import CLIConfig
from .file_models import FetchedFile, DiffResult
from .glossary_models import Glossary
from .translation_models import TranslationResult


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None


@dataclass
class AgentState:
    """State maintained by the Translation Agent."""

    config: CLIConfig
    fetched_files: List[FetchedFile] = field(default_factory=list)
    diff_result: Optional[DiffResult] = None
    glossary: Optional[Glossary] = None
    current_file: Optional[str] = None
    current_language: Optional[str] = None
    results: Dict[str, Dict[str, TranslationResult]] = field(default_factory=dict)
    errors: List[Exception] = field(default_factory=list)
