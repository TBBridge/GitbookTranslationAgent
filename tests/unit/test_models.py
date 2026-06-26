from pathlib import Path

import pytest
from pydantic import ValidationError

from gitbook_translator.models import (
    FileLanguageResult,
    PipelineResult,
    ProgressEvent,
    ProviderSpec,
    RunStatus,
    TranslationIssue,
    TranslationJob,
)


def _translation_job_kwargs(**overrides):
    kwargs = {
        "repo_url": "https://github.com/acme/docs",
        "branch": "main",
        "target_paths": ["docs"],
        "languages": ["en"],
        "dictionary_path": Path("dictionaries/default"),
        "output_root": Path("translated"),
        "translation_provider": ProviderSpec(provider="ollama", model="qwen3"),
    }
    kwargs.update(overrides)
    return kwargs


def test_run_status_derives_exit_code():
    assert RunStatus.SUCCEEDED.exit_code == 0
    assert RunStatus.FAILED.exit_code == 1
    assert RunStatus.PARTIAL.exit_code == 2
    assert RunStatus.CANCELLED.exit_code == 2


def test_models_round_trip_through_json():
    provider = ProviderSpec(provider="ollama", model="qwen3")
    job = TranslationJob(
        repo_url="https://github.com/acme/docs",
        branch="main",
        target_paths=["docs"],
        languages=["en"],
        dictionary_path=Path("dictionaries/default"),
        output_root=Path("translated"),
        translation_provider=provider,
    )
    event = ProgressEvent(
        kind="stage",
        stage="translate",
        message="Translating docs/index.md",
        current=1,
        total=1,
        file_path="docs/index.md",
        language="en",
    )
    issue = TranslationIssue(
        code="provider_timeout",
        message="Provider request timed out",
        stage="translate",
        file_path="docs/index.md",
        language="en",
        retriable=True,
    )
    result = PipelineResult(
        status=RunStatus.PARTIAL,
        results=[
            FileLanguageResult(
                source_path="docs/index.md",
                language="en",
                status=RunStatus.FAILED,
                issues=[issue],
            )
        ],
        issues=[issue],
    )

    assert TranslationJob.model_validate_json(job.model_dump_json()) == job
    assert ProgressEvent.model_validate_json(event.model_dump_json()) == event
    assert PipelineResult.model_validate_json(result.model_dump_json()) == result
    assert result.success_count == 0
    assert result.failure_count == 1


def test_provider_spec_rejects_blank_identifiers():
    with pytest.raises(ValidationError):
        ProviderSpec(provider=" ", model="qwen3")


def test_translation_job_rejects_blank_target_path_entries():
    with pytest.raises(ValidationError):
        TranslationJob(**_translation_job_kwargs(target_paths=[" "]))


def test_translation_job_rejects_blank_language_entries():
    with pytest.raises(ValidationError):
        TranslationJob(**_translation_job_kwargs(languages=[" "]))
