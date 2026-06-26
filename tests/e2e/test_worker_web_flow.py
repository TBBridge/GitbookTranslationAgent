from __future__ import annotations

import os
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

from gitbook_translator.models import (
    FileLanguageResult,
    PipelineResult,
    ProgressEvent,
    RunStatus,
)
from gitbook_translator.worker.client import WorkerControlPlaneClient
from gitbook_translator.worker.config import parse_worker_config
from gitbook_translator.worker.outbox import Outbox
from gitbook_translator.worker.runner import WorkerRunner


ADMIN_PASSWORD_HASH = (
    "$argon2id$v=19$m=19456,t=2,p=1$30lSHveygLyH7to88CU5nQ"
    "$KrxyHdMmzkD4eR2rloEOM6gzlVPhU5oaR7EiEIByVa4"
)
EXPECTED_TRANSLATION = "# Hello from the local worker\n"


class FakePipeline:
    def __init__(self, output_file: Path) -> None:
        self.output_file = output_file

    def run(self, job, emit, should_cancel=None):
        emit(ProgressEvent(kind="stage", stage="translate", message="fake translation"))
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text(EXPECTED_TRANSLATION, encoding="utf-8")
        return PipelineResult(
            status=RunStatus.SUCCEEDED,
            results=[
                FileLanguageResult(
                    source_path="README.md",
                    language="en",
                    status=RunStatus.SUCCEEDED,
                    output_path=str(self.output_file),
                )
            ],
        )


def test_python_worker_completes_job_against_real_web_control_plane(tmp_path):
    port = free_port()
    server_url = f"http://127.0.0.1:{port}"

    with next_server(port):
        with httpx.Client(base_url=server_url, follow_redirects=False) as admin:
            csrf_token = login(admin, server_url)
            job = create_job(admin, csrf_token)

            config = worker_config(tmp_path, server_url)
            output_file = tmp_path / "output" / "README.en.md"
            runner = WorkerRunner(
                client=WorkerControlPlaneClient(
                    server_url=server_url,
                    token="worker-secret",
                    worker_version="pytest-worker",
                ),
                pipeline=FakePipeline(output_file),
                config=config,
                outbox=Outbox(tmp_path / "outbox.jsonl"),
            )

            result = runner.run_once()
            final_job = admin.get(f"/api/admin/jobs/{job['id']}").json()

        assert result.status == RunStatus.SUCCEEDED
        assert final_job["state"] == "succeeded"
        assert output_file.read_text(encoding="utf-8") == EXPECTED_TRANSLATION


def login(client: httpx.Client, server_url: str) -> str:
    response = client.post(
        "/api/admin/login",
        headers={"origin": server_url},
        json={"password": "correct-password"},
    )
    response.raise_for_status()
    session = response.headers["set-cookie"].split("admin_session=", 1)[1].split(";", 1)[0]
    client.cookies.set("admin_session", session, domain="127.0.0.1", path="/")
    return response.json()["csrfToken"]


def create_job(client: httpx.Client, csrf_token: str) -> dict:
    response = client.post(
        "/api/admin/jobs",
        headers={"origin": str(client.base_url).rstrip("/"), "x-csrf-token": csrf_token},
        json={
            "schemaVersion": 1,
            "repoUrl": "https://github.com/acme/docs",
            "branch": "main",
            "targetPaths": ["README.md"],
            "languages": ["en"],
            "dictionarySet": "default",
            "outputRoot": "default",
            "translationProvider": "ollama-local",
            "reviewProvider": None,
            "pushStrategy": "none",
            "confirmDirectPush": False,
        },
    )
    response.raise_for_status()
    return response.json()


def worker_config(tmp_path: Path, server_url: str):
    dictionary_root = tmp_path / "dicts"
    dictionary_root.mkdir()
    (dictionary_root / "dictionary_en.json").write_text(
        '{"翻訳":"Translation"}',
        encoding="utf-8",
    )
    return parse_worker_config(
        {
            "server_url": server_url,
            "worker_name": "pytest-worker",
            "dictionaries": {"default": str(dictionary_root)},
            "output_roots": {"default": str(tmp_path / "output")},
            "providers": [
                {
                    "name": "ollama-local",
                    "provider": "ollama",
                    "model": "qwen3",
                    "roles": ["translate", "review"],
                }
            ],
        },
        base_dir=tmp_path,
    )


@contextmanager
def next_server(port: int):
    env = {
        **os.environ,
        "ADMIN_PASSWORD_HASH": ADMIN_PASSWORD_HASH,
        "E2E_IN_MEMORY": "1",
        "FORCE_COLOR": "0",
        "NO_COLOR": "1",
        "WORKER_TOKEN": "worker-secret",
    }
    process = subprocess.Popen(
        [
            "npm",
            "run",
            "dev",
            "--",
            "--hostname",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=Path(__file__).parents[2] / "web",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_server(f"http://127.0.0.1:{port}/login")
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def wait_for_server(url: str) -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=1)
            if response.status_code < 500:
                return
        except httpx.HTTPError:
            time.sleep(0.2)
    raise TimeoutError(f"server did not become ready: {url}")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
