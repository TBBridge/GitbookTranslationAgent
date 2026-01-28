"""Unit tests for DetectFileChangesTool."""

import os
import json
import tempfile
import pytest
from datetime import datetime

from src.tools.detect_file_changes import DetectFileChangesTool
from src.models.file_models import FetchedFile, FileMetadata


@pytest.fixture
def detect_tool():
    """Create DetectFileChangesTool instance."""
    return DetectFileChangesTool()


@pytest.fixture
def sample_fetched_file():
    """Create a sample FetchedFile."""
    return FetchedFile(
        path="docs/intro.md",
        content="# Introduction\n\nThis is a test.",
        commit_hash="abc123def456",
        last_modified=datetime(2024, 1, 15, 10, 30, 0)
    )


@pytest.fixture
def sample_file_dict():
    """Create a sample file dictionary."""
    return {
        "path": "docs/intro.md",
        "content": "# Introduction\n\nThis is a test.",
        "commit_hash": "abc123def456",
        "last_modified": "2024-01-15T10:30:00"
    }


def test_parse_fetched_files_single_file(detect_tool, sample_file_dict):
    """Test parsing a single file dictionary."""
    files = detect_tool._parse_fetched_files([sample_file_dict])
    
    assert len(files) == 1
    assert files[0].path == "docs/intro.md"
    assert files[0].content == "# Introduction\n\nThis is a test."
    assert files[0].commit_hash == "abc123def456"
    assert isinstance(files[0].last_modified, datetime)


def test_parse_fetched_files_multiple_files(detect_tool):
    """Test parsing multiple file dictionaries."""
    files_data = [
        {
            "path": "README.md",
            "content": "# README",
            "commit_hash": "aaa111",
            "last_modified": "2024-01-01T00:00:00"
        },
        {
            "path": "docs/guide.md",
            "content": "# Guide",
            "commit_hash": "bbb222",
            "last_modified": "2024-01-02T00:00:00"
        }
    ]
    
    files = detect_tool._parse_fetched_files(files_data)
    
    assert len(files) == 2
    assert files[0].path == "README.md"
    assert files[1].path == "docs/guide.md"


def test_load_cache_nonexistent_file(detect_tool):
    """Test loading cache when file doesn't exist."""
    metadata = detect_tool._load_cache("nonexistent_cache.json")
    
    assert metadata == []


def test_load_cache_valid_file(detect_tool):
    """Test loading cache from valid file."""
    cache_data = {
        "version": "1.0",
        "last_run": "2024-01-15T10:00:00",
        "files": [
            {
                "path": "docs/intro.md",
                "commit_hash": "abc123",
                "last_modified": "2024-01-15T09:00:00",
                "translated_languages": ["en"],
                "translations": {
                    "en": {
                        "outputPath": "output/docs/intro.en.md",
                        "translatedAt": "2024-01-15T09:30:00"
                    }
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_path = f.name
        json.dump(cache_data, f)
    
    try:
        metadata = detect_tool._load_cache(cache_path)
        
        assert len(metadata) == 1
        assert metadata[0].path == "docs/intro.md"
        assert metadata[0].commit_hash == "abc123"
        assert metadata[0].translated_languages == ["en"]
        assert "en" in metadata[0].translations
    finally:
        os.unlink(cache_path)


def test_load_cache_corrupted_file(detect_tool):
    """Test loading cache from corrupted file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_path = f.name
        f.write("{ invalid json }")
    
    try:
        metadata = detect_tool._load_cache(cache_path)
        
        # Should return empty list on error
        assert metadata == []
    finally:
        os.unlink(cache_path)


def test_detect_changes_first_run_all_new(detect_tool):
    """Test first run where all files are new."""
    current_files = [
        FetchedFile(
            path="README.md",
            content="# README",
            commit_hash="aaa111",
            last_modified=datetime.now()
        ),
        FetchedFile(
            path="docs/intro.md",
            content="# Intro",
            commit_hash="bbb222",
            last_modified=datetime.now()
        )
    ]
    
    cached_metadata = []  # Empty cache (first run)
    
    diff_result = detect_tool._detect_changes(current_files, cached_metadata)
    
    assert len(diff_result.new_files) == 2
    assert len(diff_result.modified_files) == 0
    assert len(diff_result.unchanged_files) == 0


def test_detect_changes_all_unchanged(detect_tool):
    """Test subsequent run where all files are unchanged."""
    current_files = [
        FetchedFile(
            path="README.md",
            content="# README",
            commit_hash="aaa111",
            last_modified=datetime.now()
        )
    ]
    
    cached_metadata = [
        FileMetadata(
            path="README.md",
            commit_hash="aaa111",
            last_modified=datetime.now(),
            translated_languages=[],
            translations={}
        )
    ]
    
    diff_result = detect_tool._detect_changes(current_files, cached_metadata)
    
    assert len(diff_result.new_files) == 0
    assert len(diff_result.modified_files) == 0
    assert len(diff_result.unchanged_files) == 1


def test_detect_changes_file_modified(detect_tool):
    """Test subsequent run with modified file."""
    current_files = [
        FetchedFile(
            path="README.md",
            content="# README Updated",
            commit_hash="aaa222",  # Different commit hash
            last_modified=datetime.now()
        )
    ]
    
    cached_metadata = [
        FileMetadata(
            path="README.md",
            commit_hash="aaa111",  # Old commit hash
            last_modified=datetime.now(),
            translated_languages=[],
            translations={}
        )
    ]
    
    diff_result = detect_tool._detect_changes(current_files, cached_metadata)
    
    assert len(diff_result.new_files) == 0
    assert len(diff_result.modified_files) == 1
    assert len(diff_result.unchanged_files) == 0
    assert diff_result.modified_files[0].path == "README.md"


def test_detect_changes_mixed_files(detect_tool):
    """Test with mix of new, modified, and unchanged files."""
    current_files = [
        FetchedFile(
            path="README.md",
            content="# README",
            commit_hash="aaa111",
            last_modified=datetime.now()
        ),
        FetchedFile(
            path="docs/intro.md",
            content="# Intro Updated",
            commit_hash="bbb333",  # Modified
            last_modified=datetime.now()
        ),
        FetchedFile(
            path="docs/new.md",
            content="# New",
            commit_hash="ccc111",  # New file
            last_modified=datetime.now()
        )
    ]
    
    cached_metadata = [
        FileMetadata(
            path="README.md",
            commit_hash="aaa111",  # Unchanged
            last_modified=datetime.now(),
            translated_languages=[],
            translations={}
        ),
        FileMetadata(
            path="docs/intro.md",
            commit_hash="bbb222",  # Old commit
            last_modified=datetime.now(),
            translated_languages=[],
            translations={}
        )
    ]
    
    diff_result = detect_tool._detect_changes(current_files, cached_metadata)
    
    assert len(diff_result.new_files) == 1
    assert len(diff_result.modified_files) == 1
    assert len(diff_result.unchanged_files) == 1
    assert diff_result.new_files[0].path == "docs/new.md"
    assert diff_result.modified_files[0].path == "docs/intro.md"
    assert diff_result.unchanged_files[0].path == "README.md"


def test_save_cache_creates_file(detect_tool):
    """Test saving cache creates file."""
    files = [
        FetchedFile(
            path="README.md",
            content="# README",
            commit_hash="aaa111",
            last_modified=datetime(2024, 1, 15, 10, 0, 0)
        )
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = os.path.join(tmpdir, "cache.json")
        
        detect_tool.save_cache(cache_path, files)
        
        assert os.path.exists(cache_path)
        
        # Verify content
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        
        assert cache_data["version"] == "1.0"
        assert len(cache_data["files"]) == 1
        assert cache_data["files"][0]["path"] == "README.md"
        assert cache_data["files"][0]["commit_hash"] == "aaa111"


def test_save_cache_preserves_translation_info(detect_tool):
    """Test saving cache preserves existing translation info."""
    # Create initial cache with translation info
    initial_cache = {
        "version": "1.0",
        "last_run": "2024-01-15T10:00:00",
        "files": [
            {
                "path": "README.md",
                "commit_hash": "aaa111",
                "last_modified": "2024-01-15T09:00:00",
                "translated_languages": ["en", "zh-CN"],
                "translations": {
                    "en": {
                        "outputPath": "output/README.en.md",
                        "translatedAt": "2024-01-15T09:30:00"
                    }
                }
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_path = f.name
        json.dump(initial_cache, f)
    
    try:
        # Update cache with new commit hash
        files = [
            FetchedFile(
                path="README.md",
                content="# README Updated",
                commit_hash="aaa222",  # New commit
                last_modified=datetime(2024, 1, 16, 10, 0, 0)
            )
        ]
        
        detect_tool.save_cache(cache_path, files)
        
        # Verify translation info is preserved
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        
        assert cache_data["files"][0]["commit_hash"] == "aaa222"
        assert cache_data["files"][0]["translated_languages"] == ["en", "zh-CN"]
        assert "en" in cache_data["files"][0]["translations"]
    finally:
        os.unlink(cache_path)


def test_run_first_run_all_new(detect_tool):
    """Test _run method on first run (all files new)."""
    current_files = [
        {
            "path": "README.md",
            "content": "# README",
            "commit_hash": "aaa111",
            "last_modified": "2024-01-15T10:00:00"
        }
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = os.path.join(tmpdir, "cache.json")
        
        result_json = detect_tool._run(current_files, cache_path)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert len(result["new_files"]) == 1
        assert len(result["modified_files"]) == 0
        assert len(result["unchanged_files"]) == 0
        assert result["summary"]["new_count"] == 1
        assert result["summary"]["total_count"] == 1


def test_run_subsequent_run_with_changes(detect_tool):
    """Test _run method on subsequent run with changes."""
    # Create initial cache
    cache_data = {
        "version": "1.0",
        "last_run": "2024-01-15T10:00:00",
        "files": [
            {
                "path": "README.md",
                "commit_hash": "aaa111",
                "last_modified": "2024-01-15T09:00:00",
                "translated_languages": [],
                "translations": {}
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_path = f.name
        json.dump(cache_data, f)
    
    try:
        # Run with modified file
        current_files = [
            {
                "path": "README.md",
                "content": "# README Updated",
                "commit_hash": "aaa222",  # Different commit
                "last_modified": "2024-01-16T10:00:00"
            }
        ]
        
        result_json = detect_tool._run(current_files, cache_path)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert len(result["new_files"]) == 0
        assert len(result["modified_files"]) == 1
        assert len(result["unchanged_files"]) == 0
        assert result["modified_files"][0]["path"] == "README.md"
        assert result["modified_files"][0]["commit_hash"] == "aaa222"
    finally:
        os.unlink(cache_path)


def test_run_cache_persistence(detect_tool):
    """Test that cache persists across runs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = os.path.join(tmpdir, "cache.json")
        
        # First run
        current_files = [
            {
                "path": "README.md",
                "content": "# README",
                "commit_hash": "aaa111",
                "last_modified": "2024-01-15T10:00:00"
            }
        ]
        
        result1_json = detect_tool._run(current_files, cache_path)
        result1 = json.loads(result1_json)
        
        # Save cache manually (simulating what would happen in real workflow)
        files = detect_tool._parse_fetched_files(current_files)
        detect_tool.save_cache(cache_path, files)
        
        # Second run with same file
        result2_json = detect_tool._run(current_files, cache_path)
        result2 = json.loads(result2_json)
        
        # First run: file is new
        assert len(result1["new_files"]) == 1
        
        # Second run: file is unchanged
        assert len(result2["unchanged_files"]) == 1
        assert len(result2["new_files"]) == 0


def test_run_error_handling(detect_tool):
    """Test error handling in _run method."""
    # Invalid input (missing required fields)
    invalid_files = [
        {
            "path": "README.md"
            # Missing other required fields
        }
    ]
    
    result_json = detect_tool._run(invalid_files, "cache.json")
    result = json.loads(result_json)
    
    assert "error" in result
    assert result["new_files"] == []
    assert result["modified_files"] == []
    assert result["unchanged_files"] == []
