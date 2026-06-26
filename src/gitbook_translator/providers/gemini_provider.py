"""Google Gemini provider adapter."""

from __future__ import annotations

import json
import os
from typing import Any

from .base import (
    CorrectionRequest,
    ProviderConfigurationError,
    ProviderHealth,
    ReviewRequest,
    ReviewResponse,
    SegmentResponse,
    TranslationRequest,
    segment_response_from_payload,
)


class GeminiProvider:
    """Provider adapter for Google Gemini via google-genai."""

    name = "gemini"

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ProviderConfigurationError("GOOGLE_API_KEY is required for Gemini")

        from google import genai

        self.model = model
        client_kwargs: dict[str, Any] = {"api_key": key}
        if base_url:
            client_kwargs["http_options"] = {"base_url": base_url}
        self._client = genai.Client(**client_kwargs)

    def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            model=self.model,
            available=True,
            message="client configured",
        )

    def translate(self, request: TranslationRequest) -> SegmentResponse:
        payload = self._generate_json("translate", request.model_dump())
        return segment_response_from_payload(
            [segment.id for segment in request.segments],
            payload,
        )

    def review(self, request: ReviewRequest) -> ReviewResponse:
        payload = self._generate_json("review", request.model_dump())
        return ReviewResponse.model_validate(payload)

    def correct(self, request: CorrectionRequest) -> SegmentResponse:
        payload = self._generate_json("correct", request.model_dump())
        return segment_response_from_payload(
            [segment.id for segment in request.segments],
            payload,
        )

    def _generate_json(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Return only valid JSON for the requested deterministic "
            f"translation {task} task.\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True)
        )
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        parsed = json.loads(response.text or "")
        if not isinstance(parsed, dict):
            raise ValueError("Gemini response JSON must be an object")
        return parsed


__all__ = ["GeminiProvider"]
