from pathlib import Path

from gitbook_translator.dictionaries import LoadedDictionary
from gitbook_translator.github_client import FetchResult, SourceFile
from gitbook_translator.models import ProviderSpec, RunStatus, TranslationJob
from gitbook_translator.pipeline import TranslationPipeline
from gitbook_translator.providers.base import SegmentResponse, SegmentTranslation


class Source:
    def fetch(self, patterns, branch):
        return FetchResult(
            status="succeeded",
            files=[SourceFile(path="README.md", content="帳票定義を開く")],
        )


class Provider:
    name = "fake"
    model = "fake-model"

    def translate(self, request):
        return SegmentResponse(
            segments=[
                SegmentTranslation(
                    id=segment.id,
                    translation=segment.text.replace("帳票定義を開く", "Open Template Form"),
                )
                for segment in request.segments
            ]
        )


class Storage:
    def __init__(self):
        self.outputs = {}

    def save(self, path, content):
        self.outputs[str(path)] = content


def test_pipeline_flow_saves_verified_translation():
    storage = Storage()
    pipeline = TranslationPipeline(
        source=Source(),
        provider_factory=lambda spec: Provider(),
        dictionary_loader=lambda directory, language: LoadedDictionary(
            terms={"帳票定義": "Template Form"},
            sha256="dictionary",
        ),
        storage=storage,
    )
    result = pipeline.run(
        TranslationJob(
            repo_url="https://github.com/acme/docs",
            branch="main",
            target_paths=["README.md"],
            languages=["en"],
            dictionary_path=Path("dictionaries/default"),
            output_root=Path("out"),
            translation_provider=ProviderSpec(provider="ollama", model="qwen3"),
        )
    )

    assert result.status == RunStatus.SUCCEEDED
    assert list(storage.outputs.values()) == ["Open Template Form"]
