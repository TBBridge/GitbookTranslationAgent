"""Markdown parsing data models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class SegmentType(Enum):
    """Type of markdown segment."""

    PROTECTED = "protected"
    TRANSLATABLE = "translatable"


@dataclass
class SegmentMetadata:
    """Metadata for a markdown segment."""

    protection_reason: Optional[str] = None
    link_url: Optional[str] = None
    alt_text: Optional[str] = None


@dataclass
class Segment:
    """A segment of markdown content."""

    type: SegmentType
    content: str
    start_line: int
    end_line: int
    metadata: Optional[SegmentMetadata] = None


@dataclass
class StructureInfo:
    """Structure information for markdown reconstruction."""

    line_breaks: List[int] = field(default_factory=list)
    indentation: Dict[int, int] = field(default_factory=dict)
    whitespace: Dict[int, str] = field(default_factory=dict)


@dataclass
class ParsedMarkdown:
    """Parsed markdown with segments and structure."""

    segments: List[Segment] = field(default_factory=list)
    structure: StructureInfo = field(default_factory=StructureInfo)
