"""Typed inputs, progress events, issues, and pipeline results."""

from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


_NonBlankString = Annotated[str, Field(min_length=1)]


class ContractModel(BaseModel):
    """Base configuration for serialized public contracts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RunStatus(str, Enum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def exit_code(self) -> int:
        return {
            RunStatus.SUCCEEDED: 0,
            RunStatus.FAILED: 1,
            RunStatus.PARTIAL: 2,
            RunStatus.CANCELLED: 2,
        }[self]


class ProviderSpec(ContractModel):
    """Provider and model selected for one pipeline role."""

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: str | None = Field(default=None, min_length=1)


class TranslationJob(ContractModel):
    """Validated pipeline input shared by the CLI and worker."""

    repo_url: str = Field(min_length=1)
    branch: str = Field(default="main", min_length=1)
    target_paths: list[_NonBlankString] = Field(min_length=1)
    languages: list[_NonBlankString] = Field(min_length=1)
    dictionary_path: Path
    output_root: Path
    translation_provider: ProviderSpec
    review_provider: ProviderSpec | None = None


class ProgressEvent(ContractModel):
    """Structured progress emitted by the deterministic pipeline."""

    kind: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    message: str | None = None
    current: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, ge=0)
    file_path: str | None = None
    language: str | None = None

    @model_validator(mode="after")
    def validate_progress_bounds(self) -> "ProgressEvent":
        if (
            self.current is not None
            and self.total is not None
            and self.current > self.total
        ):
            raise ValueError("current progress cannot exceed total")
        return self


class TranslationIssue(ContractModel):
    """A structured problem associated with a pipeline stage or result."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    stage: str | None = None
    file_path: str | None = None
    language: str | None = None
    retriable: bool = False


class FileLanguageResult(ContractModel):
    """Outcome for one source file and target-language pair."""

    source_path: str = Field(min_length=1)
    language: str = Field(min_length=1)
    status: RunStatus
    output_path: str | None = None
    cache_hit: bool = False
    issues: list[TranslationIssue] = Field(default_factory=list)


class PipelineResult(ContractModel):
    """Aggregate outcome returned by the translation pipeline."""

    status: RunStatus
    results: list[FileLanguageResult] = Field(default_factory=list)
    issues: list[TranslationIssue] = Field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(result.status == RunStatus.SUCCEEDED for result in self.results)

    @property
    def failure_count(self) -> int:
        return sum(result.status == RunStatus.FAILED for result in self.results)
