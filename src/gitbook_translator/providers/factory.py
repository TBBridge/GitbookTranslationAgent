"""Provider factory with lazy adapter imports."""

from __future__ import annotations

from gitbook_translator.models import ProviderSpec

from .base import ProviderConfigurationError, TranslationProvider


def create_provider(spec: ProviderSpec) -> TranslationProvider:
    """Create the selected provider without importing unselected provider SDKs."""

    provider = spec.provider.lower()
    if provider == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider(model=spec.model, base_url=spec.base_url)

    if provider == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(model=spec.model, base_url=spec.base_url)

    if provider in {"gemini", "google", "google-gemini"}:
        from .gemini_provider import GeminiProvider

        return GeminiProvider(model=spec.model, base_url=spec.base_url)

    raise ProviderConfigurationError(f"Unknown provider: {spec.provider}")


__all__ = ["ProviderConfigurationError", "create_provider"]
