"""Tool for detecting file changes using cache."""

import os
import json
from typing import List, Dict, Any
from datetime import datetime

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from ..models.file_models import FetchedFile, FileMetadata, DiffResult


class DetectFileChangesInput(BaseModel):
    """Input schema for DetectFileChangesTool."""

    current_files: List[Dict[str, Any]] = Field(
        description="List of currently fetched files with path, content, commit_hash, last_modified"
    )
    cache_path: str = Field(
        default=".gitbook-translator-cache.json",
        description="Path to cache file"
    )


class DetectFileChangesTool(BaseTool):
    """Tool for detecting file changes by comparing with cached metadata."""

    name: str = "detect_file_changes"
    description: str = """
    Detects changes in files by comparing current files with cached metadata.
    Input should be a JSON with: current_files (list of file dicts), cache_path (optional).
    Returns categorized files as new, modified, or unchanged.
    """
    args_schema: type[BaseModel] = DetectFileChangesInput

    def _run(
        self,
        current_files: List[Dict[str, Any]],
        cache_path: str = ".gitbook-translator-cache.json"
    ) -> str:
        """Execute the tool to detect file changes.
        
        Args:
            current_files: List of currently fetched files as dictionaries
            cache_path: Path to cache file
            
        Returns:
            JSON string containing categorized files (new, modified, unchanged)
        """
        try:
            # Convert dict format to FetchedFile objects
            fetched_files = self._parse_fetched_files(current_files)
            
            # Load cached metadata
            cached_metadata = self._load_cache(cache_path)
            
            # Detect changes
            diff_result = self._detect_changes(fetched_files, cached_metadata)
            
            # Convert result to JSON-serializable format
            result_data = {
                "success": True,
                "new_files": [
                    {
                        "path": f.path,
                        "content": f.content,
                        "commit_hash": f.commit_hash,
                        "last_modified": f.last_modified.isoformat()
                    }
                    for f in diff_result.new_files
                ],
                "modified_files": [
                    {
                        "path": f.path,
                        "content": f.content,
                        "commit_hash": f.commit_hash,
                        "last_modified": f.last_modified.isoformat()
                    }
                    for f in diff_result.modified_files
                ],
                "unchanged_files": [
                    {
                        "path": f.path,
                        "content": f.content,
                        "commit_hash": f.commit_hash,
                        "last_modified": f.last_modified.isoformat()
                    }
                    for f in diff_result.unchanged_files
                ],
                "summary": {
                    "new_count": len(diff_result.new_files),
                    "modified_count": len(diff_result.modified_files),
                    "unchanged_count": len(diff_result.unchanged_files),
                    "total_count": len(fetched_files)
                }
            }
            
            return json.dumps(result_data)
            
        except Exception as e:
            return json.dumps({
                "error": f"Failed to detect file changes: {str(e)}",
                "new_files": [],
                "modified_files": [],
                "unchanged_files": []
            })

    def _parse_fetched_files(self, files_data: List[Dict[str, Any]]) -> List[FetchedFile]:
        """Parse file dictionaries into FetchedFile objects.
        
        Args:
            files_data: List of file dictionaries
            
        Returns:
            List of FetchedFile objects
        """
        fetched_files = []
        for file_dict in files_data:
            # Parse last_modified from ISO format string
            last_modified_str = file_dict.get("last_modified", "")
            if isinstance(last_modified_str, str):
                last_modified = datetime.fromisoformat(last_modified_str.replace('Z', '+00:00'))
            else:
                last_modified = last_modified_str
            
            fetched_file = FetchedFile(
                path=file_dict["path"],
                content=file_dict["content"],
                commit_hash=file_dict["commit_hash"],
                last_modified=last_modified
            )
            fetched_files.append(fetched_file)
        
        return fetched_files

    def _load_cache(self, cache_path: str) -> List[FileMetadata]:
        """Load cached file metadata from JSON file.
        
        Args:
            cache_path: Path to cache file
            
        Returns:
            List of FileMetadata objects, empty list if cache doesn't exist
        """
        if not os.path.exists(cache_path):
            return []
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            metadata_list = []
            for file_data in cache_data.get("files", []):
                # Parse last_modified from ISO format
                last_modified = datetime.fromisoformat(
                    file_data["last_modified"].replace('Z', '+00:00')
                )
                
                metadata = FileMetadata(
                    path=file_data["path"],
                    commit_hash=file_data["commit_hash"],
                    last_modified=last_modified,
                    translated_languages=file_data.get("translated_languages", []),
                    translations=file_data.get("translations", {})
                )
                metadata_list.append(metadata)
            
            return metadata_list
            
        except Exception as e:
            # If cache is corrupted, return empty list
            return []

    def _detect_changes(
        self,
        current_files: List[FetchedFile],
        cached_metadata: List[FileMetadata]
    ) -> DiffResult:
        """Detect changes by comparing current files with cached metadata.
        
        Args:
            current_files: List of currently fetched files
            cached_metadata: List of cached file metadata
            
        Returns:
            DiffResult with categorized files
        """
        # Create lookup dictionary for cached metadata
        cache_dict = {meta.path: meta for meta in cached_metadata}
        
        diff_result = DiffResult()
        
        for current_file in current_files:
            if current_file.path not in cache_dict:
                # File is new
                diff_result.new_files.append(current_file)
            else:
                cached_meta = cache_dict[current_file.path]
                if current_file.commit_hash != cached_meta.commit_hash:
                    # File has been modified
                    diff_result.modified_files.append(current_file)
                else:
                    # File is unchanged
                    diff_result.unchanged_files.append(current_file)
        
        return diff_result

    def save_cache(
        self,
        cache_path: str,
        files: List[FetchedFile],
        languages: List[str] = None
    ) -> None:
        """Save file metadata to cache.
        
        Args:
            cache_path: Path to cache file
            files: List of files to cache
            languages: List of languages that were translated (optional)
        """
        if languages is None:
            languages = []
        
        # Load existing cache to preserve translation info
        existing_cache = self._load_cache(cache_path)
        existing_dict = {meta.path: meta for meta in existing_cache}
        
        # Update metadata
        cache_data = {
            "version": "1.0",
            "last_run": datetime.now().isoformat(),
            "files": []
        }
        
        for file in files:
            # Preserve existing translation info if available
            existing_meta = existing_dict.get(file.path)
            
            file_data = {
                "path": file.path,
                "commit_hash": file.commit_hash,
                "last_modified": file.last_modified.isoformat(),
                "translated_languages": existing_meta.translated_languages if existing_meta else [],
                "translations": existing_meta.translations if existing_meta else {}
            }
            
            cache_data["files"].append(file_data)
        
        # Ensure directory exists
        cache_dir = os.path.dirname(cache_path)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        
        # Write cache file
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

    async def _arun(self, *args, **kwargs) -> str:
        """Async execution (not implemented)."""
        raise NotImplementedError("Async execution not supported")
