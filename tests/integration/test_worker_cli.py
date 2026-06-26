from __future__ import annotations

import subprocess
import sys
from unittest.mock import Mock

from gitbook_translator import cli
from gitbook_translator.models import PipelineResult, RunStatus
from gitbook_translator.worker.runner import WorkerRunner


def test_worker_help_lists_config_and_once_options():
    result = subprocess.run(
        [sys.executable, "-m", "gitbook_translator.cli", "worker", "--help"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--config" in result.stdout
    assert "--once" in result.stdout


def test_worker_sigint_returns_130(monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "worker-secret")
    monkeypatch.setattr(
        WorkerRunner,
        "run_forever",
        Mock(side_effect=KeyboardInterrupt),
    )

    assert cli.main(["worker", "--config", "worker.example.toml"]) == 130


def test_worker_once_returns_pipeline_status(monkeypatch):
    monkeypatch.setenv("WORKER_TOKEN", "worker-secret")
    monkeypatch.setattr(
        WorkerRunner,
        "run_once",
        Mock(return_value=PipelineResult(status=RunStatus.SUCCEEDED)),
    )

    assert cli.main(["worker", "--config", "worker.example.toml", "--once"]) == 0


def test_worker_missing_token_returns_error(monkeypatch, capsys):
    monkeypatch.delenv("WORKER_TOKEN", raising=False)

    assert cli.main(["worker", "--config", "worker.example.toml", "--once"]) == 1
    assert "WORKER_TOKEN" in capsys.readouterr().err
