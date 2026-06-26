"""Explicit GitHub fetch and publish result adapters."""

from __future__ import annotations

import fnmatch
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FetchStatus = Literal["succeeded", "partial", "failed"]
PublishStatus = Literal["succeeded", "skipped", "failed"]
PublishStrategy = Literal[
    "none",
    "push_same_repo_direct",
    "push_same_repo_new_branch",
]


class DirectPushNotConfirmed(ValueError):
    """Raised when direct push is requested without explicit confirmation."""


class GitHubModel(BaseModel):
    """Base model for GitHub adapter contracts."""

    model_config = ConfigDict(extra="forbid")


class SourceFile(GitHubModel):
    """Fetched source file."""

    path: str = Field(min_length=1)
    content: str
    sha: str | None = None


class FetchError(GitHubModel):
    """Explicit fetch error for one path or operation."""

    path: str = ""
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    status: int | None = None


class FetchResult(GitHubModel):
    """Result of fetching source files."""

    status: FetchStatus
    files: list[SourceFile] = Field(default_factory=list)
    errors: list[FetchError] = Field(default_factory=list)


class OutputFile(GitHubModel):
    """File prepared for publication."""

    path: str = Field(min_length=1)
    content: str


class PublishResult(GitHubModel):
    """Result of publishing translated files."""

    status: PublishStatus
    branch: str
    files: list[str] = Field(default_factory=list)
    compare_url: str | None = None
    message: str = ""


class GitHubSource:
    """Fetch Markdown source files from a repository-like object."""

    def __init__(self, repository) -> None:
        self.repository = repository

    def fetch(self, patterns: list[str], branch: str) -> FetchResult:
        try:
            paths = self._matching_paths(patterns, branch)
        except Exception as exc:  # pragma: no cover - defensive boundary
            return FetchResult(
                status="failed",
                errors=[
                    FetchError(
                        code="list_failed",
                        message=str(exc),
                        status=_exception_status(exc),
                    )
                ],
            )

        if not paths:
            return FetchResult(
                status="failed",
                errors=[
                    FetchError(
                        code="no_matching_files",
                        message="No files matched the configured target paths",
                    )
                ],
            )

        files: list[SourceFile] = []
        errors: list[FetchError] = []
        for path in paths:
            try:
                content = self.repository.get_contents(path, ref=branch)
                files.append(_source_file_from_content(path, content))
            except Exception as exc:
                errors.append(
                    FetchError(
                        path=path,
                        code="fetch_failed",
                        message=str(exc),
                        status=_exception_status(exc),
                    )
                )

        if files and errors:
            status: FetchStatus = "partial"
        elif errors:
            status = "failed"
        else:
            status = "succeeded"

        return FetchResult(status=status, files=files, errors=errors)

    def _matching_paths(self, patterns: list[str], branch: str) -> list[str]:
        if hasattr(self.repository, "list_paths"):
            available_paths = list(self.repository.list_paths(branch))
        else:
            available_paths = list(self.repository.get_git_tree(branch, recursive=True).tree)
            available_paths = [
                item.path
                for item in available_paths
                if getattr(item, "type", None) == "blob"
            ]

        return [
            path
            for path in sorted(available_paths)
            if any(_matches_pattern(path, pattern) for pattern in patterns)
        ]


class GitHubPublisher:
    """Publish translated outputs to a repository-like object."""

    def __init__(self, repository) -> None:
        self.repository = repository

    def publish(
        self,
        branch: str,
        files: list[OutputFile],
        strategy: PublishStrategy,
        direct_push_confirmed: bool = False,
        message: str = "Update translated documentation",
    ) -> PublishResult:
        if strategy == "none":
            return PublishResult(
                status="skipped",
                branch=branch,
                files=[],
                message="remote publishing disabled",
            )

        if strategy == "push_same_repo_direct" and not direct_push_confirmed:
            raise DirectPushNotConfirmed(
                "Direct push requires explicit confirmation"
            )

        target_branch = branch
        for output_file in files:
            self.repository.upsert_file(
                output_file.path,
                output_file.content,
                target_branch,
                message,
            )

        compare_url = None
        if hasattr(self.repository, "compare_url"):
            compare_url = self.repository.compare_url(target_branch)

        return PublishResult(
            status="succeeded",
            branch=target_branch,
            files=[output_file.path for output_file in files],
            compare_url=compare_url,
            message=message,
        )


def _source_file_from_content(path: str, content) -> SourceFile:
    raw = getattr(content, "decoded_content", b"")
    if isinstance(raw, bytes):
        text = raw.decode("utf-8")
    elif isinstance(raw, str):
        text = raw
    else:
        text = str(raw)
    return SourceFile(path=path, content=text, sha=getattr(content, "sha", None))


def _exception_status(exc: Exception) -> int | None:
    status = getattr(exc, "status", None)
    return status if isinstance(status, int) else None


def _matches_pattern(path: str, pattern: str) -> bool:
    if fnmatch.fnmatch(path, pattern):
        return True
    if "/**/" in pattern:
        direct_pattern = pattern.replace("/**/", "/")
        return fnmatch.fnmatch(path, direct_pattern)
    return False


__all__ = [
    "DirectPushNotConfirmed",
    "FetchError",
    "FetchResult",
    "GitHubPublisher",
    "GitHubSource",
    "OutputFile",
    "PublishResult",
    "SourceFile",
]
