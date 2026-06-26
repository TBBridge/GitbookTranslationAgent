import pytest

from gitbook_translator.models import ProviderSpec
from gitbook_translator.providers.factory import (
    ProviderConfigurationError,
    create_provider,
)


def test_factory_does_not_require_unselected_provider_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    provider = create_provider(ProviderSpec(provider="ollama", model="qwen3"))

    assert provider.name == "ollama"
    assert provider.model == "qwen3"


def test_factory_rejects_unknown_provider():
    with pytest.raises(ProviderConfigurationError):
        create_provider(ProviderSpec(provider="unknown", model="x"))


def test_factory_requires_key_for_selected_openai_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ProviderConfigurationError, match="OPENAI_API_KEY"):
        create_provider(ProviderSpec(provider="openai", model="gpt-4.1-mini"))


def test_factory_requires_key_for_selected_gemini_provider(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(ProviderConfigurationError, match="GOOGLE_API_KEY"):
        create_provider(ProviderSpec(provider="gemini", model="gemini-2.5-flash"))
