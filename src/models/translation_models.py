"""Translation-related data models."""

from dataclasses import dataclass, field
from typing import List

from .markdown_models import Segment, StructureInfo
from .glossary_models import Glossary


@dataclass
class TranslationRequest:
    """Request for translation."""

    segments: List[Segment]
    target_language: str
    glossary: Glossary
    structure: StructureInfo


@dataclass
class TranslationResult:
    """Result of translation."""

    translated_segments: List[Segment] = field(default_factory=list)
    reconstructed_content: str = ""
