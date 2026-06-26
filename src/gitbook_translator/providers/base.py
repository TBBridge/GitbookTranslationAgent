"""Shared provider contracts."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from gitbook_translator.markdown import validate_segment_response


class ProviderConfigurationError(ValueError):
    """Raised when a selected provider is misconfigured."""


class ProviderModel(BaseModel):
    """Base model for provider request/response contracts."""

    model_config = ConfigDict(extra="forbid")


class SegmentInput(ProviderModel):
    """One source segment to translate."""

    id: str = Field(min_length=1)
    text: str


class TranslationRequest(ProviderModel):
    """Structured translation request sent to providers."""

    language: str = Field(min_length=1)
    segments: list[SegmentInput] = Field(min_length=1)
    dictionary: dict[str, str] = Field(default_factory=dict)


class ReviewRequest(TranslationRequest):
    """Structured review request."""

    translated_markdown: str = ""


class CorrectionRequest(TranslationRequest):
    """Structured correction request."""

    issues: list[dict[str, Any]] = Field(default_factory=list)


class SegmentTranslation(ProviderModel):
    """One translated segment returned by a provider."""

    id: str = Field(min_length=1)
    translation: str


class SegmentResponse(ProviderModel):
    """Validated segment translation response."""

    segments: list[SegmentTranslation]


class ReviewResponse(ProviderModel):
    """Validated review response."""

    approved: bool
    issues: list[dict[str, Any]] = Field(default_factory=list)


class ProviderHealth(ProviderModel):
    """Provider availability and diagnostics."""

    provider: str
    model: str
    available: bool
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class TranslationProvider(Protocol):
    """Common provider interface used by the pipeline."""

    name: str
    model: str

    def healthcheck(self) -> ProviderHealth:
        """Return provider availability."""

    def translate(self, request: TranslationRequest) -> SegmentResponse:
        """Translate source segments."""

    def review(self, request: ReviewRequest) -> ReviewResponse:
        """Review translated output."""

    def correct(self, request: CorrectionRequest) -> SegmentResponse:
        """Correct translated segments."""


def segment_response_from_payload(
    expected_ids: list[str],
    payload: dict[str, Any],
) -> SegmentResponse:
    """Validate provider JSON and preserve the original requested segment order."""

    translations = validate_segment_response(set(expected_ids), payload)
    return SegmentResponse(
        segments=[
            SegmentTranslation(id=segment_id, translation=translations[segment_id])
            for segment_id in expected_ids
        ]
    )


__all__ = [
    "CorrectionRequest",
    "ProviderConfigurationError",
    "ProviderHealth",
    "ReviewRequest",
    "ReviewResponse",
    "SegmentInput",
    "SegmentResponse",
    "SegmentTranslation",
    "TranslationProvider",
    "TranslationRequest",
    "segment_response_from_payload",
]
