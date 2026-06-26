"""Typed local worker configuration and public capability payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ProviderRole = Literal["translate", "review"]


def _snake_to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class WorkerModel(BaseModel):
    """Base model for worker contracts."""

    model_config = ConfigDict(
        alias_generator=lambda value: _snake_to_camel(value),
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


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


class RegisterResponse(WorkerModel):
    """Control-plane response after worker registration."""

    worker_id: str = Field(min_length=1)


class WorkerJobConfig(WorkerModel):
    """Versioned job configuration created by the web control plane."""

    schema_version: int = 1
    repo_url: str = Field(min_length=1)
    branch: str = Field(default="main", min_length=1)
    target_paths: list[str] = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    dictionary_set: str = Field(min_length=1)
    output_root: str = Field(min_length=1)
    cache_root: str | None = Field(default=None, min_length=1)
    translation_provider: str = Field(min_length=1)
    review_provider: str | None = Field(default=None, min_length=1)


class ClaimedJob(WorkerModel):
    """One exclusively leased translation job."""

    job_id: str = Field(min_length=1)
    lease_id: str = Field(min_length=1)
    lease_expires_at: str = Field(min_length=1)
    config: WorkerJobConfig


class ClaimResponse(WorkerModel):
    """Result of a claim attempt. ``job`` is absent when the queue is empty."""

    job: ClaimedJob | None = None


class HeartbeatResponse(WorkerModel):
    """Control-plane heartbeat acknowledgement."""

    accepted: bool = True


class RenewResponse(WorkerModel):
    """Lease-renewal acknowledgement."""

    accepted: bool = True
    lease_expires_at: str | None = Field(default=None, min_length=1)


class UpdateAck(WorkerModel):
    """Acknowledgement for delivered progress events."""

    acknowledged_sequence: int = Field(default=0, ge=0)


class CancellationState(WorkerModel):
    """Current cancellation state for a leased job."""

    cancelled: bool = False


class CompleteResponse(WorkerModel):
    """Acknowledgement for job completion."""

    accepted: bool = True
    acknowledged_sequence: int | None = Field(default=None, ge=0)


__all__ = [
    "CancellationState",
    "ClaimResponse",
    "ClaimedJob",
    "CompleteResponse",
    "DictionarySetCapability",
    "HeartbeatResponse",
    "ProviderCapability",
    "ProviderRole",
    "RegisterResponse",
    "RenewResponse",
    "UpdateAck",
    "WorkerCapabilities",
    "WorkerConfig",
    "WorkerDictionarySet",
    "WorkerJobConfig",
    "WorkerModel",
    "WorkerProviderConfig",
]
