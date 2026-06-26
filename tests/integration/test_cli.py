import pytest

from gitbook_translator import cli
from gitbook_translator.models import PipelineResult, RunStatus


VALID_ARGS = [
    "translate",
    "--repo-url",
    "https://github.com/acme/docs",
    "--target-paths",
    "docs/**/*.md",
    "--languages",
    "en",
    "--dictionary-path",
    "dictionaries/default",
    "--output-root",
    "out",
    "--provider",
    "ollama",
    "--model",
    "qwen3",
]


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (RunStatus.SUCCEEDED, 0),
        (RunStatus.FAILED, 1),
        (RunStatus.PARTIAL, 2),
    ],
)
def test_cli_returns_pipeline_exit_code(monkeypatch, status, code):
    monkeypatch.setattr(cli, "run_translation", lambda _: PipelineResult(status=status))

    assert cli.main(VALID_ARGS) == code


def test_cli_accepts_translate_as_default_operation(monkeypatch):
    monkeypatch.setattr(
        cli,
        "run_translation",
        lambda _: PipelineResult(status=RunStatus.SUCCEEDED),
    )

    assert cli.main(VALID_ARGS[1:]) == 0


def test_glossary_flag_has_migration_error(capsys):
    code = cli.main(["translate", "--glossary-path", "glossary.json"])

    assert code == 1
    assert "use --dictionary-path" in capsys.readouterr().err


def test_openai_provider_requires_only_openai_key(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "unused-google-key")

    code = cli.main([*VALID_ARGS, "--provider", "openai", "--model", "gpt-4.1-mini"])

    assert code == 1
    assert "OPENAI_API_KEY" in capsys.readouterr().err


def test_ollama_provider_does_not_require_cloud_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(
        cli,
        "run_translation",
        lambda _: PipelineResult(status=RunStatus.SUCCEEDED),
    )

    assert cli.main(VALID_ARGS) == 0
