"""Configuration validation helpers for deterministic translation runs."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_repository_url(value: str) -> str:
    """Return a canonical HTTP(S) repository URL without ``.git`` or slash suffixes."""
    repository_url = value.strip()
    if not repository_url:
        raise ValueError("repository URL is required")

    parsed = urlparse(repository_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("repository URL must be an absolute HTTP(S) URL")
    if parsed.params or parsed.query or parsed.fragment:
        raise ValueError("repository URL must not include params, query, or fragment")
    if ";" in parsed.path:
        raise ValueError("repository URL must not include params, query, or fragment")

    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not path or path == "/":
        raise ValueError("repository URL must include an owner and repository path")

    relative_path = path[1:] if path.startswith("/") else path
    path_segments = relative_path.split("/")
    if len(path_segments) != 2 or any(not segment for segment in path_segments):
        raise ValueError("repository URL must include exactly an owner and repository path")

    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def validate_branch(value: str) -> str:
    """Validate a branch/ref name while allowing ordinary slash-separated refs."""
    branch = value.strip()
    if not branch:
        raise ValueError("branch is required")
    if branch != value:
        raise ValueError("branch must not include leading or trailing whitespace")
    if branch.startswith("/") or branch.endswith("/"):
        raise ValueError("branch must not start or end with '/'")
    if ".." in branch:
        raise ValueError("branch must not contain '..'")
    if "//" in branch:
        raise ValueError("branch must not contain empty path segments")
    if "@{" in branch:
        raise ValueError("branch must not contain '@{'")
    if any(ord(character) < 32 or ord(character) == 127 for character in branch):
        raise ValueError("branch must not contain control characters")

    for segment in branch.split("/"):
        if segment.endswith("."):
            raise ValueError("branch segments must not end with '.'")
        if segment.endswith(".lock"):
            raise ValueError("branch segments must not end with '.lock'")

    return branch


__all__ = ["normalize_repository_url", "validate_branch"]
