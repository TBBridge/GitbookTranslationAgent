from pathlib import Path

from gitbook_translator.dictionaries import LoadedDictionary
from gitbook_translator.github_client import FetchResult, SourceFile
from gitbook_translator.models import ProviderSpec, RunStatus, TranslationJob
from gitbook_translator.pipeline import TranslationPipeline
from gitbook_translator.providers.base import (
    SegmentResponse,
    SegmentTranslation,
)


class FakeSource:
    def fetch(self, patterns, branch):
        return FetchResult(
            status="succeeded",
            files=[SourceFile(path="docs/index.md", content="前文")],
        )


class FakeDictionaryLoader:
    def __call__(self, directory, language):
        return LoadedDictionary(terms={}, sha256=f"dict-{language}")


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, failures):
        self.failures = failures

    def translate(self, request):
        if request.language in self.failures:
            raise RuntimeError(f"failed {request.language}")
        return SegmentResponse(
            segments=[
                SegmentTranslation(
                    id=segment.id,
                    translation=f"{request.language}:{segment.text}",
                )
                for segment in request.segments
            ]
        )


class FakeProviders:
    def __init__(self):
        self.failures = set()

    def fail_language(self, language):
        self.failures.add(language)

    def __call__(self, spec):
        return FakeProvider(self.failures)


class FakeStorage:
    def __init__(self):
        self.saved = []

    def save(self, path, content):
        self.saved.append((Path(path), content))


class Fakes:
    def __init__(self):
        self.source = FakeSource()
        self.providers = FakeProviders()
        self.storage = FakeStorage()
        self.dictionary_loader = FakeDictionaryLoader()

    def kwargs(self):
        return {
            "source": self.source,
            "provider_factory": self.providers,
            "storage": self.storage,
            "dictionary_loader": self.dictionary_loader,
            "verifier": lambda original, translated, dictionary, language: [],
        }


def job(**overrides):
    values = {
        "repo_url": "https://github.com/acme/docs",
        "branch": "main",
        "target_paths": ["docs/**/*.md"],
        "languages": ["en"],
        "dictionary_path": Path("dictionaries/default"),
        "output_root": Path("out"),
        "translation_provider": ProviderSpec(provider="ollama", model="qwen3"),
    }
    values.update(overrides)
    return TranslationJob(**values)


def test_pipeline_uses_fixed_stage_order():
    fakes = Fakes()
    events = []

    result = TranslationPipeline(**fakes.kwargs()).run(job(), events.append)

    assert [event.stage for event in events if event.kind == "stage"] == [
        "validate",
        "fetch",
        "dictionary",
        "translate",
        "verify",
        "save",
        "complete",
    ]
    assert result.status == RunStatus.SUCCEEDED


def test_one_language_failure_produces_partial():
    fakes = Fakes()
    fakes.providers.fail_language("zh-CN")

    result = TranslationPipeline(**fakes.kwargs()).run(
        job(languages=["en", "zh-CN"]),
    )

    assert result.status == RunStatus.PARTIAL
    assert result.success_count == 1
    assert result.failure_count == 1
