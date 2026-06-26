"""Deterministic mechanical translation verification."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from gitbook_translator.markdown import parse_markdown


Severity = Literal["BLOCKER", "MAJOR", "MINOR"]

_LINK_PATTERN = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
_JAPANESE_PATTERN = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


class VerificationIssue(BaseModel):
    """One deterministic verification issue."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: Severity
    message: str = Field(min_length=1)
    language: str
    original: str | None = None
    translated: str | None = None


def verify_translation(
    original: str,
    translated: str,
    dictionary: dict[str, str],
    language: str,
) -> list[VerificationIssue]:
    """Run deterministic checks that LLM approval cannot override."""

    issues: list[VerificationIssue] = []
    issues.extend(_verify_link_destinations(original, translated, language))
    issues.extend(_verify_protected_spans(original, translated, language))
    issues.extend(_verify_dictionary_terms(original, translated, dictionary, language))
    issues.extend(_verify_untranslated_japanese(translated, language))
    return issues


def _verify_link_destinations(
    original: str,
    translated: str,
    language: str,
) -> list[VerificationIssue]:
    original_links = _link_destinations(original)
    translated_links = _link_destinations(translated)
    if original_links == translated_links:
        return []

    return [
        VerificationIssue(
            code="link_changed",
            severity="BLOCKER",
            message="Markdown link destinations changed during translation",
            language=language,
            original=", ".join(original_links),
            translated=", ".join(translated_links),
        )
    ]


def _verify_protected_spans(
    original: str,
    translated: str,
    language: str,
) -> list[VerificationIssue]:
    original_spans = _protected_contents(original)
    translated_spans = _protected_contents(translated)
    if original_spans == translated_spans:
        return []

    return [
        VerificationIssue(
            code="protected_changed",
            severity="BLOCKER",
            message="Protected Markdown spans changed during translation",
            language=language,
            original="\n".join(original_spans),
            translated="\n".join(translated_spans),
        )
    ]


def _verify_dictionary_terms(
    original: str,
    translated: str,
    dictionary: dict[str, str],
    language: str,
) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    for source_term, target_term in dictionary.items():
        if source_term in original and target_term not in translated:
            issues.append(
                VerificationIssue(
                    code="dictionary_violation",
                    severity="MAJOR",
                    message=(
                        "Required dictionary translation is missing from translated text"
                    ),
                    language=language,
                    original=source_term,
                    translated=target_term,
                )
            )
    return issues


def _verify_untranslated_japanese(
    translated: str,
    language: str,
) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    document = parse_markdown(translated)
    for segment in document.translatable_segments:
        if _JAPANESE_PATTERN.search(segment.text):
            issues.append(
                VerificationIssue(
                    code="untranslated_japanese",
                    severity="MAJOR",
                    message="Translated text still contains Japanese characters",
                    language=language,
                    translated=segment.text,
                )
            )
    return issues


def _link_destinations(markdown: str) -> list[str]:
    return [match.group(1) for match in _LINK_PATTERN.finditer(markdown)]


def _protected_contents(markdown: str) -> list[str]:
    document = parse_markdown(markdown)
    return [
        part.content
        for part in document.parts
        if part.kind == "protected" and part.content.strip()
    ]


__all__ = ["VerificationIssue", "verify_translation"]
