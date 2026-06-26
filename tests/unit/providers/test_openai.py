import builtins

from gitbook_translator.models import ProviderSpec
from gitbook_translator.providers.factory import create_provider


def test_ollama_factory_branch_does_not_import_openai(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "openai" or name.startswith("openai."):
            raise AssertionError("openai should not be imported for ollama provider")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    create_provider(ProviderSpec(provider="ollama", model="qwen3"))
