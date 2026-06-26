"""Typed local worker configuration and public capability payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ProviderRole = Literal["translate", "review"]


class WorkerModel(BaseModel):
    """Base model for worker contracts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WorkerDictionarySet(WorkerModel):
    """Local dictionary-set configuration."""

    path: Path
    languages: list[str] = Field(default_factory=list)


class WorkerProviderConfig(WorkerModel):
    """Local provider declaration for jobs leased by the worker."""

    name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: str | None = Field(default=None, min_length=1)
    roles: list[ProviderRole] = Field(default_factory=lambda: ["translate"])

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, roles: list[ProviderRole]) -> list[ProviderRole]:
        if not roles:
            raise ValueError("provider roles are required")
        return sorted(set(roles), key=roles.index)


class DictionarySetCapability(WorkerModel):
    """Dictionary-set metadata safe to send to the control plane."""

    languages: list[str] = Field(default_factory=list)


class ProviderCapability(WorkerModel):
    """Provider metadata safe to send to the control plane."""

    name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    roles: list[ProviderRole] = Field(default_factory=list)


class WorkerCapabilities(WorkerModel):
    """Capability payload published by a local worker."""

    schema_version: int = 1
    worker_name: str = Field(min_length=1)
    dictionary_sets: dict[str, DictionarySetCapability] = Field(default_factory=dict)
    output_roots: list[str] = Field(default_factory=list)
    providers: list[ProviderCapability] = Field(default_factory=list)


class WorkerConfig(WorkerModel):
    """Resolved local worker configuration."""

    server_url: str = Field(min_length=1)
    worker_name: str = Field(default="gitbook-translator-worker", min_length=1)
    token_env: str = Field(default="WORKER_TOKEN", min_length=1)
    poll_interval_seconds: float = Field(default=5.0, gt=0)
    heartbeat_interval_seconds: float = Field(default=30.0, gt=0)
    lease_renewal_seconds: float = Field(default=20.0, gt=0)
    request_timeout_seconds: float = Field(default=30.0, gt=0)
    dictionaries: dict[str, WorkerDictionarySet] = Field(default_factory=dict)
    output_roots: dict[str, Path] = Field(default_factory=dict)
    cache_roots: dict[str, Path] = Field(default_factory=dict)
    providers: list[WorkerProviderConfig] = Field(default_factory=list)
    capabilities: WorkerCapabilities

    @property
    def dictionary_sets(self) -> dict[str, WorkerDictionarySet]:
        """Backward-readable alias used by the runner."""

        return self.dictionaries

    @model_validator(mode="after")
    def validate_required_capabilities(self) -> "WorkerConfig":
        if not self.providers:
            raise ValueError("at least one provider is required")
        if not any("translate" in provider.roles for provider in self.providers):
            raise ValueError("at least one translate provider is required")
        return self


__all__ = [
    "DictionarySetCapability",
    "ProviderCapability",
    "ProviderRole",
    "WorkerCapabilities",
    "WorkerConfig",
    "WorkerDictionarySet",
    "WorkerModel",
    "WorkerProviderConfig",
]
