from __future__ import annotations

from pathlib import Path

import pytest

from gitbook_translator.worker.config import load_worker_config, parse_worker_config


def worker_toml(tmp_path: Path) -> Path:
    config_path = tmp_path / "worker.toml"
    dictionary_root = tmp_path / "dictionaries" / "default"
    output_root = tmp_path / "output"
    cache_root = tmp_path / "cache"
    config_path.write_text(
        f"""
server_url = "https://control.test"
worker_name = "local-worker"
token_env = "WORKER_TOKEN"
poll_interval_seconds = 2
heartbeat_interval_seconds = 20
lease_renewal_seconds = 15

[dictionaries]
default = "{dictionary_root}"

[output_roots]
default = "{output_root}"

[cache_roots]
default = "{cache_root}"

[[providers]]
name = "ollama-local"
provider = "ollama"
model = "qwen3"
base_url = "http://127.0.0.1:11434"
roles = ["translate", "review"]
""",
        encoding="utf-8",
    )
    return config_path


def test_worker_discovers_dictionary_languages(tmp_path):
    root = tmp_path / "dictionaries" / "default"
    root.mkdir(parents=True)
    (root / "dictionary_en.json").write_text('{"翻訳":"Translation"}')

    config = load_worker_config(worker_toml(tmp_path))

    assert config.capabilities.dictionary_sets["default"].languages == ["en"]


def test_worker_rejects_output_root_name_with_escape(tmp_path):
    with pytest.raises(ValueError):
        parse_worker_config({"output_roots": {"../bad": str(tmp_path)}})


def test_worker_capabilities_do_not_expose_local_paths_or_token(tmp_path):
    root = tmp_path / "dictionaries" / "default"
    root.mkdir(parents=True)
    (root / "dictionary_en.json").write_text('{"翻訳":"Translation"}')

    capabilities = load_worker_config(worker_toml(tmp_path)).capabilities.model_dump()
    serialized = repr(capabilities)

    assert str(tmp_path) not in serialized
    assert "WORKER_TOKEN" not in serialized


def test_worker_resolves_config_relative_paths(tmp_path):
    config_dir = tmp_path / "config"
    dictionary_root = config_dir / "dictionaries" / "default"
    dictionary_root.mkdir(parents=True)
    (dictionary_root / "dictionary_zh-cn.json").write_text('{"翻訳":"翻译"}')
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "worker.toml"
    config_path.write_text(
        """
server_url = "https://control.test"
worker_name = "relative-worker"

[dictionaries]
default = "./dictionaries/default"

[output_roots]
default = "./output"

[[providers]]
name = "ollama-local"
provider = "ollama"
model = "qwen3"
roles = ["translate"]
""",
        encoding="utf-8",
    )

    config = load_worker_config(config_path)

    assert config.dictionary_sets["default"].path == dictionary_root.resolve()
    assert config.output_roots["default"] == (config_dir / "output").resolve()
    assert config.capabilities.dictionary_sets["default"].languages == ["zh-CN"]


def test_worker_rejects_provider_without_translate_role():
    with pytest.raises(ValueError):
        parse_worker_config(
            {
                "server_url": "https://control.test",
                "worker_name": "worker",
                "providers": [
                    {
                        "name": "review-only",
                        "provider": "ollama",
                        "model": "qwen3",
                        "roles": ["review"],
                    }
                ],
            }
        )
