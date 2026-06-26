"""Path construction helpers with output-root containment checks."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath


def resolve_output_path(
    output_root: Path | str,
    source_path: str,
    language: str,
    output_mode: str,
) -> Path:
    """Resolve a deterministic output path for a source file and language."""
    if output_mode != "directory":
        raise ValueError("unsupported output mode")

    source = _safe_relative_source_path(source_path)
    generated = Path(output_root) / language / Path(*source.parts)

    root = Path(output_root).resolve()
    candidate = generated.resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("output path escapes configured root")

    return candidate


def _safe_relative_source_path(source_path: str) -> PurePosixPath:
    if "\\" in source_path:
        raise ValueError("source path must use POSIX separators")
    if PureWindowsPath(source_path).drive:
        raise ValueError("source path must not include a Windows drive")

    source = PurePosixPath(source_path)
    if source.is_absolute():
        raise ValueError("source path must be relative")
    if not source.parts:
        raise ValueError("source path is required")
    if ".." in source.parts:
        raise ValueError("source path must not contain '..'")

    return source


__all__ = ["resolve_output_path"]
