"""Ollama HTTP provider adapter."""

from __future__ import annotations

import json
from typing import Any

import httpx

from .base import (
    CorrectionRequest,
    ProviderHealth,
    ReviewRequest,
    ReviewResponse,
    SegmentResponse,
    TranslationRequest,
    segment_response_from_payload,
)


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


class OllamaProvider:
    """Provider adapter for a local Ollama server."""

    name = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.base_url = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            transport=transport,
            timeout=timeout,
        )

    def healthcheck(self) -> ProviderHealth:
        response = self._client.get("/api/tags")
        response.raise_for_status()
        payload = response.json()
        models = {
            model.get("name")
            for model in payload.get("models", [])
            if isinstance(model, dict)
        }
        if self.model in models:
            return ProviderHealth(
                provider=self.name,
                model=self.model,
                available=True,
                message="model available",
            )
        return ProviderHealth(
            provider=self.name,
            model=self.model,
            available=False,
            message=f"Ollama model not found: {self.model}",
            details={"available_models": sorted(name for name in models if name)},
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
        response = self._client.post(
            "/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "messages": [
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
            },
        )
        response.raise_for_status()
        content = response.json().get("message", {}).get("content")
        if not isinstance(content, str):
            raise ValueError("Ollama response did not include message.content")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("Ollama response JSON must be an object")
        return parsed


__all__ = ["DEFAULT_OLLAMA_URL", "OllamaProvider"]
