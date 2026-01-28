"""Tool for saving translated files."""

import json
import os
from pathlib import Path
from typing import Literal
from datetime import datetime

from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class SaveTranslationInput(BaseModel):
    """Input schema for SaveTranslationTool."""

    original_path: str = Field(description="Original file path from repository")
    content: str = Field(description="Translated content to save")
    language: str = Field(description="Target language code (e.g., 'en', 'zh-CN')")
    output_root: str = Field(description="Root directory for output files")
    naming_convention: Literal["suffix", "directory"] = Field(
        description="Naming convention: 'suffix' for <name>.<lang>.md or 'directory' for /<lang>/<path>"
    )
    cache_path: str = Field(
        default=".gitbook-translator-cache.json",
        description="Path to cache file for updating metadata"
    )
    commit_hash: str = Field(
        default="",
        description="Commit hash of the source file"
    )


class SaveTranslationTool(BaseTool):
    """Tool for saving translated content to files with appropriate naming conventions."""

    name: str = "save_translation"
    description: str = """
    Saves translated content to a file with appropriate naming convention.
    Input should be a JSON with: original_path (string), content (string), language (string), output_root (string), naming_convention (string).
    Returns saved file path and success status.
    """
    args_schema: type[BaseModel] = SaveTranslationInput

    def _run(
        self,
        original_path: str,
        content: str,
        language: str,
        output_root: str,
        naming_convention: Literal["suffix", "directory"] = "suffix",
        cache_path: str = ".gitbook-translator-cache.json",
        commit_hash: str = ""
    ) -> str:
        """Execute the tool to save translated content.
        
        Args:
            original_path: Original file path from repository (e.g., 'docs/intro.md')
            content: Translated content to save
            language: Target language code (e.g., 'en', 'zh-CN', 'zh-TW')
            output_root: Root directory for output files
            naming_convention: 'suffix' for <name>.<lang>.md or 'directory' for /<lang>/<path>
            cache_path: Path to cache file for updating metadata
            commit_hash: Commit hash of the source file
            
        Returns:
            JSON string containing saved file path and success status
        """
        try:
            # Generate output path based on naming convention
            output_path = self._generate_output_path(
                original_path,
                language,
                output_root,
                naming_convention
            )
            
            # Create parent directories if they don't exist
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write translated content to file
            output_file.write_text(content, encoding='utf-8')
            
            # Update cache metadata after successful save
            self._update_cache_metadata(
                cache_path=cache_path,
                original_path=original_path,
                language=language,
                output_path=output_path,
                commit_hash=commit_hash
            )
            
            return json.dumps({
                "success": True,
                "saved_path": str(output_path),
                "original_path": original_path,
                "language": language,
                "naming_convention": naming_convention
            })
            
        except PermissionError as e:
            return json.dumps({
                "success": False,
                "error": f"Permission denied: {str(e)}",
                "saved_path": None
            })
        except OSError as e:
            return json.dumps({
                "success": False,
                "error": f"File system error: {str(e)}",
                "saved_path": None
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "saved_path": None
            })

    def _generate_output_path(
        self,
        original_path: str,
        language: str,
        output_root: str,
        naming_convention: Literal["suffix", "directory"]
    ) -> str:
        """Generate output file path based on naming convention.
        
        Args:
            original_path: Original file path (e.g., 'docs/intro.md')
            language: Target language code (e.g., 'en', 'zh-CN')
            output_root: Root directory for output files
            naming_convention: 'suffix' or 'directory'
            
        Returns:
            Full output file path
        """
        original_path_obj = Path(original_path)
        output_root_obj = Path(output_root)
        
        if naming_convention == "suffix":
            # Suffix mode: docs/intro.md -> {output_root}/docs/intro.en.md
            # Split filename and extension
            stem = original_path_obj.stem  # 'intro'
            suffix = original_path_obj.suffix  # '.md'
            parent = original_path_obj.parent  # 'docs'
            
            # Create new filename with language suffix
            new_filename = f"{stem}.{language}{suffix}"
            
            # Combine with output root and preserve directory structure
            output_path = output_root_obj / parent / new_filename
            
        else:  # directory mode
            # Directory mode: docs/intro.md -> {output_root}/en/docs/intro.md
            output_path = output_root_obj / language / original_path
        
        return str(output_path)

    def _update_cache_metadata(
        self,
        cache_path: str,
        original_path: str,
        language: str,
        output_path: str,
        commit_hash: str
    ) -> None:
        """Update cache metadata after successful translation save.
        
        Args:
            cache_path: Path to cache file
            original_path: Original file path from repository
            language: Target language code
            output_path: Path where translation was saved
            commit_hash: Commit hash of the source file
        """
        # Load existing cache or create new one
        cache_data = self._load_cache(cache_path)
        
        # Find or create file entry
        file_entry = None
        for entry in cache_data.get("files", []):
            if entry["path"] == original_path:
                file_entry = entry
                break
        
        if file_entry is None:
            # Create new entry if file not in cache
            file_entry = {
                "path": original_path,
                "commit_hash": commit_hash,
                "last_modified": datetime.now().isoformat(),
                "translated_languages": [],
                "translations": {}
            }
            cache_data["files"].append(file_entry)
        
        # Update translation info
        if language not in file_entry["translated_languages"]:
            file_entry["translated_languages"].append(language)
        
        file_entry["translations"][language] = {
            "output_path": output_path,
            "translated_at": datetime.now().isoformat()
        }
        
        # Update last_run timestamp
        cache_data["last_run"] = datetime.now().isoformat()
        
        # Save updated cache
        self._save_cache(cache_path, cache_data)

    def _load_cache(self, cache_path: str) -> dict:
        """Load cache from file.
        
        Args:
            cache_path: Path to cache file
            
        Returns:
            Cache data dictionary
        """
        if not os.path.exists(cache_path):
            return {
                "version": "1.0",
                "last_run": datetime.now().isoformat(),
                "files": []
            }
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            # If cache is corrupted, return empty cache
            return {
                "version": "1.0",
                "last_run": datetime.now().isoformat(),
                "files": []
            }

    def _save_cache(self, cache_path: str, cache_data: dict) -> None:
        """Save cache to file.
        
        Args:
            cache_path: Path to cache file
            cache_data: Cache data to save
        """
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
