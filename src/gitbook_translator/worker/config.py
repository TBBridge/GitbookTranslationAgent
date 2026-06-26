"""TOML loading and capability discovery for local workers."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from gitbook_translator.worker.models import (
    DictionarySetCapability,
    ProviderCapability,
    WorkerCapabilities,
    WorkerConfig,
    WorkerDictionarySet,
    WorkerProviderConfig,
)


_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_DICTIONARY_FILE_RE = re.compile(r"^dictionary_([A-Za-z0-9][A-Za-z0-9-]*)\.json$")
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_worker_config(path: str | Path) -> WorkerConfig:
    """Load and resolve a worker TOML file."""

    config_path = Path(path).expanduser().resolve()
    with config_path.open("rb") as file:
        data = tomllib.load(file)
    return parse_worker_config(data, base_dir=config_path.parent)


def parse_worker_config(
    data: dict[str, Any],
    *,
    base_dir: str | Path | None = None,
) -> WorkerConfig:
    """Parse already-loaded worker configuration data."""

    if not isinstance(data, dict):
        raise ValueError("worker config must be a TOML object")

    root = Path(base_dir).expanduser().resolve() if base_dir else Path.cwd().resolve()
    server_url = _validate_server_url(str(data.get("server_url", "")))
    worker_name = str(data.get("worker_name", "gitbook-translator-worker"))
    token_env = _validate_env_name(str(data.get("token_env", "WORKER_TOKEN")))
    dictionaries = _parse_dictionary_sets(data.get("dictionaries", {}), root)
    output_roots = _parse_path_map(data.get("output_roots", {}), root, "output root")
    cache_roots = _parse_path_map(data.get("cache_roots", {}), root, "cache root")
    providers = _parse_providers(data.get("providers", []))
    capabilities = _build_capabilities(
        worker_name=worker_name,
        dictionaries=dictionaries,
        output_roots=output_roots,
        providers=providers,
    )

    raw_config = {
        "server_url": server_url,
        "worker_name": worker_name,
        "token_env": token_env,
        "poll_interval_seconds": data.get("poll_interval_seconds", 5.0),
        "heartbeat_interval_seconds": data.get("heartbeat_interval_seconds", 30.0),
        "lease_renewal_seconds": data.get("lease_renewal_seconds", 20.0),
        "request_timeout_seconds": data.get("request_timeout_seconds", 30.0),
        "dictionaries": dictionaries,
        "output_roots": output_roots,
        "cache_roots": cache_roots,
        "providers": providers,
        "capabilities": capabilities,
    }
    try:
        return WorkerConfig(**raw_config)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


def _parse_dictionary_sets(
    raw: Any,
    base_dir: Path,
) -> dict[str, WorkerDictionarySet]:
    paths = _parse_path_map(raw, base_dir, "dictionary set")
    return {
        name: WorkerDictionarySet(
            path=path,
            languages=_discover_dictionary_languages(path),
        )
        for name, path in paths.items()
    }


def _parse_path_map(raw: Any, base_dir: Path, label: str) -> dict[str, Path]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{label} declarations must be a table")

    parsed: dict[str, Path] = {}
    for name, value in raw.items():
        safe_name = _validate_name(str(name), label)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} path for {safe_name!r} must be a non-empty string")
        parsed[safe_name] = _resolve_local_path(value, base_dir)
    return parsed


def _parse_providers(raw: Any) -> list[WorkerProviderConfig]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("providers must be an array of tables")

    providers: list[WorkerProviderConfig] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("provider declarations must be TOML tables")
        name = _validate_name(str(item.get("name", "")), "provider")
        if name in seen:
            raise ValueError(f"duplicate provider name: {name}")
        seen.add(name)
        try:
            providers.append(WorkerProviderConfig(**{**item, "name": name}))
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
    return providers


def _build_capabilities(
    *,
    worker_name: str,
    dictionaries: dict[str, WorkerDictionarySet],
    output_roots: dict[str, Path],
    providers: list[WorkerProviderConfig],
) -> WorkerCapabilities:
    return WorkerCapabilities(
        worker_name=worker_name,
        dictionary_sets={
            name: DictionarySetCapability(languages=value.languages)
            for name, value in dictionaries.items()
        },
        output_roots=sorted(output_roots),
        providers=[
            ProviderCapability(
                name=provider.name,
                provider=provider.provider,
                model=provider.model,
                roles=provider.roles,
            )
            for provider in providers
        ],
    )


def _discover_dictionary_languages(path: Path) -> list[str]:
    if not path.is_dir():
        return []

    languages: set[str] = set()
    for item in path.iterdir():
        if not item.is_file():
            continue
        match = _DICTIONARY_FILE_RE.fullmatch(item.name)
        if match:
            languages.add(_canonical_language(match.group(1)))
    return sorted(languages)


def _canonical_language(language: str) -> str:
    parts = language.lower().split("-")
    if len(parts) == 1:
        return parts[0]
    return "-".join([parts[0], *[part.upper() if len(part) == 2 else part for part in parts[1:]]])


def _validate_name(name: str, label: str) -> str:
    value = name.strip()
    if not _SAFE_NAME_RE.fullmatch(value):
        raise ValueError(f"unsafe {label} name: {name!r}")
    return value


def _validate_env_name(name: str) -> str:
    value = name.strip()
    if not _ENV_NAME_RE.fullmatch(value):
        raise ValueError(f"unsafe token environment variable name: {name!r}")
    return value


def _validate_server_url(value: str) -> str:
    server_url = value.strip().rstrip("/")
    parsed = urlparse(server_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("server_url must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("server_url must not include credentials")
    return server_url


def _resolve_local_path(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


__all__ = ["load_worker_config", "parse_worker_config"]
