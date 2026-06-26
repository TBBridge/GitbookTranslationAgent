"""OpenAI provider adapter."""

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


class OpenAIProvider:
    """Provider adapter for OpenAI Chat Completions."""

    name = "openai"

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ProviderConfigurationError("OPENAI_API_KEY is required for OpenAI")

        from openai import OpenAI

        self.model = model
        client_kwargs: dict[str, str] = {"api_key": key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = OpenAI(**client_kwargs)

    def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            model=self.model,
            available=True,
            message="client configured",
        )

    def translate(self, request: TranslationRequest) -> SegmentResponse:
        payload = self._chat_json("translate", request.model_dump())
        return segment_response_from_payload(
            [segment.id for segment in request.segments],
            payload,
        )

    def review(self, request: ReviewRequest) -> ReviewResponse:
        payload = self._chat_json("review", request.model_dump())
        return ReviewResponse.model_validate(payload)

    def correct(self, request: CorrectionRequest) -> SegmentResponse:
        payload = self._chat_json("correct", request.model_dump())
        return segment_response_from_payload(
            [segment.id for segment in request.segments],
            payload,
        )

    def _chat_json(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only valid JSON for the requested deterministic "
                        f"translation {task} task."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
        )
        content = response.choices[0].message.content
        parsed = json.loads(content or "")
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI response JSON must be an object")
        return parsed


__all__ = ["OpenAIProvider"]
