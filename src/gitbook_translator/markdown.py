"""Markdown segmentation and provider response validation."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class InvalidProviderResponse(ValueError):
    """Raised when a provider segment response violates the response contract."""


class TextSegment(BaseModel):
    """A translatable text span with structural whitespace separated out."""

    model_config = ConfigDict(extra="forbid")

    id: str
    prefix: str
    text: str
    suffix: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class MarkdownPart(BaseModel):
    """One reconstruction part: either protected content or a translatable segment."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["protected", "segment"]
    content: str = ""
    segment_id: str | None = None


class MarkdownDocument(BaseModel):
    """Parsed Markdown with stable translatable segments and reconstruction parts."""

    model_config = ConfigDict(extra="forbid")

    source: str
    parts: list[MarkdownPart]
    translatable_segments: list[TextSegment]


def parse_markdown(source: str) -> MarkdownDocument:
    """Parse Markdown into protected parts and stable translatable segments."""

    protected = _protected_intervals(source)
    parts: list[MarkdownPart] = []
    segments: list[TextSegment] = []

    position = 0
    for start, end in protected:
        if position < start:
            _append_text_part(source[position:start], position, parts, segments)
        parts.append(MarkdownPart(kind="protected", content=source[start:end]))
        position = end

    if position < len(source):
        _append_text_part(source[position:], position, parts, segments)

    return MarkdownDocument(source=source, parts=parts, translatable_segments=segments)


def reconstruct(document: MarkdownDocument, translations: dict[str, str]) -> str:
    """Reconstruct Markdown from a parsed document and translated segment text."""

    segments = {segment.id: segment for segment in document.translatable_segments}
    output: list[str] = []

    for part in document.parts:
        if part.kind == "protected":
            output.append(part.content)
            continue

        if part.segment_id is None or part.segment_id not in segments:
            raise ValueError("document contains an unknown segment part")
        if part.segment_id not in translations:
            raise InvalidProviderResponse(f"Missing translation for {part.segment_id}")

        segment = segments[part.segment_id]
        translation = translations[part.segment_id]
        if not isinstance(translation, str):
            raise InvalidProviderResponse(f"Translation must be a string: {part.segment_id}")
        output.append(f"{segment.prefix}{translation}{segment.suffix}")

    return "".join(output)


def validate_segment_response(
    expected_ids: set[str],
    payload: dict[str, Any],
) -> dict[str, str]:
    """Validate a structured provider response and return id -> translation."""

    if not isinstance(payload, dict):
        raise InvalidProviderResponse("Provider response must be an object")

    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        raise InvalidProviderResponse("Provider response must contain a segments list")

    translations: dict[str, str] = {}
    for raw_segment in raw_segments:
        if not isinstance(raw_segment, dict):
            raise InvalidProviderResponse("Each provider segment must be an object")

        segment_id = raw_segment.get("id")
        if not isinstance(segment_id, str):
            raise InvalidProviderResponse("Provider segment is missing a string id")
        if segment_id not in expected_ids:
            raise InvalidProviderResponse(f"Unknown segment id: {segment_id}")
        if segment_id in translations:
            raise InvalidProviderResponse(f"Duplicate segment id: {segment_id}")

        translation = raw_segment.get("translation")
        if not isinstance(translation, str):
            raise InvalidProviderResponse(
                f"Provider segment translation must be a string: {segment_id}"
            )

        translations[segment_id] = translation

    missing = expected_ids - set(translations)
    if missing:
        missing_ids = ", ".join(sorted(missing))
        raise InvalidProviderResponse(f"Missing translations for: {missing_ids}")

    return translations


def _append_text_part(
    raw: str,
    global_start: int,
    parts: list[MarkdownPart],
    segments: list[TextSegment],
) -> None:
    chunks = re.split(r"(\n[ \t]*\n+)", raw)
    if len(chunks) > 1:
        offset = 0
        for chunk in chunks:
            if chunk:
                _append_single_text_part(chunk, global_start + offset, parts, segments)
            offset += len(chunk)
        return

    _append_single_text_part(raw, global_start, parts, segments)


def _append_single_text_part(
    raw: str,
    global_start: int,
    parts: list[MarkdownPart],
    segments: list[TextSegment],
) -> None:
    if not raw:
        return
    if not raw.strip():
        parts.append(MarkdownPart(kind="protected", content=raw))
        return

    leading = len(raw) - len(raw.lstrip())
    trailing = len(raw) - len(raw.rstrip())
    text_end = len(raw) - trailing if trailing else len(raw)
    text = raw[leading:text_end]

    segment_id = f"segment-{len(segments) + 1:04d}"
    segment = TextSegment(
        id=segment_id,
        prefix=raw[:leading],
        text=text,
        suffix=raw[text_end:],
        start=global_start + leading,
        end=global_start + text_end,
    )
    segments.append(segment)
    parts.append(MarkdownPart(kind="segment", segment_id=segment_id))


def _protected_intervals(source: str) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    intervals.extend(_yaml_frontmatter_interval(source))
    intervals.extend(_regex_intervals(source, re.compile(r"(?ms)^```[^\n]*\n.*?^```[^\n]*(?:\n|$)")))
    intervals.extend(_regex_intervals(source, re.compile(r"(?s)\{%.*?%\}")))
    intervals.extend(_regex_intervals(source, re.compile(r"(?s)\{\{.*?\}\}")))
    intervals.extend(_regex_intervals(source, re.compile(r"</?[A-Za-z!][^>\n]*?>")))
    intervals.extend(_link_destination_intervals(source))
    intervals.extend(_regex_intervals(source, re.compile(r"(?<!`)`[^`\n]+`(?!`)")))
    return _merge_intervals(intervals)


def _yaml_frontmatter_interval(source: str) -> list[tuple[int, int]]:
    if not source.startswith("---\n"):
        return []

    marker = source.find("\n---", 4)
    if marker == -1:
        return []

    end = marker + len("\n---")
    if end < len(source) and source[end] == "\n":
        end += 1
    return [(0, end)]


def _regex_intervals(source: str, pattern: re.Pattern[str]) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in pattern.finditer(source)]


def _link_destination_intervals(source: str) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    pattern = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
    for match in pattern.finditer(source):
        intervals.append((match.start(1) - 1, match.end(1) + 1))
    return intervals


def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if start >= end:
            continue
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
    return merged


__all__ = [
    "InvalidProviderResponse",
    "MarkdownDocument",
    "TextSegment",
    "parse_markdown",
    "reconstruct",
    "validate_segment_response",
]
