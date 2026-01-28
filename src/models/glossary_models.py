"""Glossary data models."""

from dataclasses import dataclass, field
from typing import Dict, Literal


@dataclass
class Glossary:
    """Glossary with term mappings."""

    format: Literal["auto-detected", "custom"] = "auto-detected"
    mappings: Dict[str, Dict[str, str]] = field(default_factory=dict)
