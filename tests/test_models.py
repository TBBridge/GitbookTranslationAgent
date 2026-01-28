"""Tests for data models."""

import pytest
from datetime import datetime

from src.models import (
    CLIConfig,
    FetchedFile,
    FileMetadata,
    DiffResult,
    Segment,
    SegmentType,
    ParsedMarkdown,
    Glossary,
)


def test_cli_config_validation():
    """Test CLIConfig validation."""
    # Valid config
    config = CLIConfig(
        repo_url="https://github.com/test/repo",
        branch="main",
        target_paths=["*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="./output",
    )
    assert config.repo_url == "https://github.com/test/repo"

    # Invalid config - empty repo_url
    with pytest.raises(ValueError, match="repo_url must be non-empty"):
        CLIConfig(
            repo_url="",
            branch="main",
            target_paths=["*.md"],
            languages=["en"],
            glossary_path="glossary.json",
            output_root="./output",
        )

    # Invalid config - empty target_paths
    with pytest.raises(ValueError, match="target_paths must contain at least one pattern"):
        CLIConfig(
            repo_url="https://github.com/test/repo",
            branch="main",
            target_paths=[],
            languages=["en"],
            glossary_path="glossary.json",
            output_root="./output",
        )


def test_fetched_file():
    """Test FetchedFile model."""
    file = FetchedFile(
        path="docs/intro.md",
        content="# Introduction",
        commit_hash="abc123",
        last_modified=datetime.now(),
    )
    assert file.path == "docs/intro.md"
    assert file.content == "# Introduction"


def test_segment():
    """Test Segment model."""
    segment = Segment(
        type=SegmentType.TRANSLATABLE,
        content="This is translatable text",
        start_line=1,
        end_line=1,
    )
    assert segment.type == SegmentType.TRANSLATABLE
    assert segment.content == "This is translatable text"


def test_glossary():
    """Test Glossary model."""
    glossary = Glossary(
        format="auto-detected",
        mappings={
            "帳票定義": {"en": "Template Form", "zh-CN": "报表定义"}
        },
    )
    assert glossary.format == "auto-detected"
    assert "帳票定義" in glossary.mappings
