"""Property-based tests for DetectFileChangesTool.

Feature: gitbook-translator, Property 14: Diff detection accuracy
Validates: Requirements 2.3, 2.4
"""

import os
import json
import tempfile
from datetime import datetime
from hypothesis import given, settings, strategies as st

from src.tools.detect_file_changes import DetectFileChangesTool
from src.models.file_models import FetchedFile, FileMetadata


# Strategy for generating valid file paths
file_path_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='/-_.'),
    min_size=1,
    max_size=50
).filter(lambda x: x and not x.startswith('/') and '..' not in x)

# Strategy for generating commit hashes (40 character hex strings)
commit_hash_strategy = st.text(
    alphabet='0123456789abcdef',
    min_size=40,
    max_size=40
)

# Strategy for generating file content
content_strategy = st.text(min_size=0, max_size=1000)


def create_fetched_file(path: str, commit_hash: str, content: str = "test content") -> FetchedFile:
    """Helper to create a FetchedFile object."""
    return FetchedFile(
        path=path,
        content=content,
        commit_hash=commit_hash,
        last_modified=datetime.now()
    )


def create_file_metadata(path: str, commit_hash: str) -> FileMetadata:
    """Helper to create a FileMetadata object."""
    return FileMetadata(
        path=path,
        commit_hash=commit_hash,
        last_modified=datetime.now(),
        translated_languages=[],
        translations={}
    )


@given(
    path=file_path_strategy,
    commit_hash=commit_hash_strategy,
    content=content_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_unchanged_commit_hash_skips_file(path: str, commit_hash: str, content: str):
    """
    Property 14: Diff detection accuracy
    
    For any file with unchanged commit hash, the system should categorize it as unchanged.
    Validates: Requirements 2.3
    """
    tool = DetectFileChangesTool()
    
    # Create a temporary cache file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_path = f.name
        cache_data = {
            "version": "1.0",
            "last_run": datetime.now().isoformat(),
            "files": [
                {
                    "path": path,
                    "commit_hash": commit_hash,
                    "last_modified": datetime.now().isoformat(),
                    "translated_languages": [],
                    "translations": {}
                }
            ]
        }
        json.dump(cache_data, f)
    
    try:
        # Create current file with same commit hash
        current_file = create_fetched_file(path, commit_hash, content)
        current_files_dict = [
            {
                "path": current_file.path,
                "content": current_file.content,
                "commit_hash": current_file.commit_hash,
                "last_modified": current_file.last_modified.isoformat()
            }
        ]
        
        # Run diff detection
        result_json = tool._run(current_files_dict, cache_path)
        result = json.loads(result_json)
        
        # Verify file is categorized as unchanged
        assert result["success"] is True
        assert len(result["unchanged_files"]) == 1
        assert result["unchanged_files"][0]["path"] == path
        assert result["unchanged_files"][0]["commit_hash"] == commit_hash
        assert len(result["new_files"]) == 0
        assert len(result["modified_files"]) == 0
        
    finally:
        # Clean up
        if os.path.exists(cache_path):
            os.unlink(cache_path)


@given(
    path=file_path_strategy,
    old_commit=commit_hash_strategy,
    new_commit=commit_hash_strategy,
    content=content_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_changed_commit_hash_marks_modified(
    path: str,
    old_commit: str,
    new_commit: str,
    content: str
):
    """
    Property 14: Diff detection accuracy
    
    For any file with changed commit hash, the system should categorize it as modified.
    Validates: Requirements 2.4
    """
    # Skip if commit hashes are the same
    if old_commit == new_commit:
        return
    
    tool = DetectFileChangesTool()
    
    # Create a temporary cache file with old commit hash
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_path = f.name
        cache_data = {
            "version": "1.0",
            "last_run": datetime.now().isoformat(),
            "files": [
                {
                    "path": path,
                    "commit_hash": old_commit,
                    "last_modified": datetime.now().isoformat(),
                    "translated_languages": [],
                    "translations": {}
                }
            ]
        }
        json.dump(cache_data, f)
    
    try:
        # Create current file with new commit hash
        current_file = create_fetched_file(path, new_commit, content)
        current_files_dict = [
            {
                "path": current_file.path,
                "content": current_file.content,
                "commit_hash": current_file.commit_hash,
                "last_modified": current_file.last_modified.isoformat()
            }
        ]
        
        # Run diff detection
        result_json = tool._run(current_files_dict, cache_path)
        result = json.loads(result_json)
        
        # Verify file is categorized as modified
        assert result["success"] is True
        assert len(result["modified_files"]) == 1
        assert result["modified_files"][0]["path"] == path
        assert result["modified_files"][0]["commit_hash"] == new_commit
        assert len(result["new_files"]) == 0
        assert len(result["unchanged_files"]) == 0
        
    finally:
        # Clean up
        if os.path.exists(cache_path):
            os.unlink(cache_path)


@given(
    path=file_path_strategy,
    commit_hash=commit_hash_strategy,
    content=content_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_new_file_without_cache_entry(path: str, commit_hash: str, content: str):
    """
    Property 14: Diff detection accuracy
    
    For any file not in cache, the system should categorize it as new.
    Validates: Requirements 2.3
    """
    tool = DetectFileChangesTool()
    
    # Create a temporary cache file with no entries
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_path = f.name
        cache_data = {
            "version": "1.0",
            "last_run": datetime.now().isoformat(),
            "files": []
        }
        json.dump(cache_data, f)
    
    try:
        # Create current file
        current_file = create_fetched_file(path, commit_hash, content)
        current_files_dict = [
            {
                "path": current_file.path,
                "content": current_file.content,
                "commit_hash": current_file.commit_hash,
                "last_modified": current_file.last_modified.isoformat()
            }
        ]
        
        # Run diff detection
        result_json = tool._run(current_files_dict, cache_path)
        result = json.loads(result_json)
        
        # Verify file is categorized as new
        assert result["success"] is True
        assert len(result["new_files"]) == 1
        assert result["new_files"][0]["path"] == path
        assert result["new_files"][0]["commit_hash"] == commit_hash
        assert len(result["modified_files"]) == 0
        assert len(result["unchanged_files"]) == 0
        
    finally:
        # Clean up
        if os.path.exists(cache_path):
            os.unlink(cache_path)


@given(
    paths=st.lists(file_path_strategy, min_size=1, max_size=10, unique=True),
    commit_hashes=st.lists(commit_hash_strategy, min_size=1, max_size=10)
)
@settings(max_examples=100, deadline=None)
def test_property_multiple_files_categorized_correctly(paths: list, commit_hashes: list):
    """
    Property 14: Diff detection accuracy
    
    For any set of files, each should be correctly categorized based on its commit hash.
    Validates: Requirements 2.3, 2.4
    """
    # Ensure we have enough commit hashes (need at least 2x paths for modified files)
    if len(commit_hashes) < len(paths) * 2:
        return
    
    tool = DetectFileChangesTool()
    
    # Create cache with some files
    cache_files = []
    current_files = []
    
    # Split files into categories - ensure we don't go out of bounds
    num_unchanged = min(len(paths) // 3, len(paths))
    num_modified = min(len(paths) // 3, len(paths) - num_unchanged)
    num_new = len(paths) - num_unchanged - num_modified
    
    # Unchanged files (same commit hash)
    for i in range(num_unchanged):
        if i >= len(paths):
            break
        path = paths[i]
        commit = commit_hashes[i]
        cache_files.append({
            "path": path,
            "commit_hash": commit,
            "last_modified": datetime.now().isoformat(),
            "translated_languages": [],
            "translations": {}
        })
        current_files.append({
            "path": path,
            "content": "content",
            "commit_hash": commit,
            "last_modified": datetime.now().isoformat()
        })
    
    # Modified files (different commit hash)
    for i in range(num_unchanged, num_unchanged + num_modified):
        if i >= len(paths):
            break
        path = paths[i]
        old_commit = commit_hashes[i]
        new_commit = commit_hashes[len(paths) + i]  # Use commit from second half
        if old_commit == new_commit:
            continue
        cache_files.append({
            "path": path,
            "commit_hash": old_commit,
            "last_modified": datetime.now().isoformat(),
            "translated_languages": [],
            "translations": {}
        })
        current_files.append({
            "path": path,
            "content": "content",
            "commit_hash": new_commit,
            "last_modified": datetime.now().isoformat()
        })
    
    # New files (not in cache)
    for i in range(num_unchanged + num_modified, len(paths)):
        if i >= len(paths):
            break
        path = paths[i]
        commit = commit_hashes[i]
        current_files.append({
            "path": path,
            "content": "content",
            "commit_hash": commit,
            "last_modified": datetime.now().isoformat()
        })
    
    # Create cache file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_path = f.name
        cache_data = {
            "version": "1.0",
            "last_run": datetime.now().isoformat(),
            "files": cache_files
        }
        json.dump(cache_data, f)
    
    try:
        # Run diff detection
        result_json = tool._run(current_files, cache_path)
        result = json.loads(result_json)
        
        # Verify categorization
        assert result["success"] is True
        
        # Total should match
        total = len(result["new_files"]) + len(result["modified_files"]) + len(result["unchanged_files"])
        assert total == len(current_files)
        
        # Each file should be in exactly one category
        all_paths = set()
        for file in result["new_files"]:
            assert file["path"] not in all_paths
            all_paths.add(file["path"])
        for file in result["modified_files"]:
            assert file["path"] not in all_paths
            all_paths.add(file["path"])
        for file in result["unchanged_files"]:
            assert file["path"] not in all_paths
            all_paths.add(file["path"])
        
    finally:
        # Clean up
        if os.path.exists(cache_path):
            os.unlink(cache_path)
