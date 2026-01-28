"""Unit tests for SaveTranslationTool."""

import json
import tempfile
from pathlib import Path

import pytest

from src.tools.save_translation import SaveTranslationTool


class TestSaveTranslationTool:
    """Test suite for SaveTranslationTool."""

    def test_save_translation_suffix_mode(self):
        """Test saving translation with suffix naming convention."""
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_json = tool._run(
                original_path="docs/test.md",
                content="# Test Content\n\nThis is a test.",
                language="en",
                output_root=tmpdir,
                naming_convention="suffix"
            )
            
            result = json.loads(result_json)
            assert result["success"] is True
            
            # Verify path structure (normalize for platform)
            saved_path = Path(result["saved_path"])
            assert saved_path.name == "test.en.md"
            assert saved_path.parent.name == "docs"
            
            # Verify file was created
            assert saved_path.exists()
            assert saved_path.read_text(encoding='utf-8') == "# Test Content\n\nThis is a test."

    def test_save_translation_directory_mode(self):
        """Test saving translation with directory naming convention."""
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_json = tool._run(
                original_path="docs/test.md",
                content="# Test Content\n\nThis is a test.",
                language="zh-CN",
                output_root=tmpdir,
                naming_convention="directory"
            )
            
            result = json.loads(result_json)
            assert result["success"] is True
            
            # Verify path structure (normalize for platform)
            saved_path = Path(result["saved_path"])
            assert saved_path.name == "test.md"
            assert saved_path.parent.name == "docs"
            assert "zh-CN" in saved_path.parts
            
            # Verify file was created
            assert saved_path.exists()
            assert saved_path.read_text(encoding='utf-8') == "# Test Content\n\nThis is a test."

    def test_save_translation_creates_directories(self):
        """Test that parent directories are created automatically."""
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_json = tool._run(
                original_path="deeply/nested/path/test.md",
                content="# Test",
                language="en",
                output_root=tmpdir,
                naming_convention="suffix"
            )
            
            result = json.loads(result_json)
            assert result["success"] is True
            
            # Verify nested directories were created
            saved_file = Path(result["saved_path"])
            assert saved_file.exists()
            assert saved_file.parent.exists()

    def test_save_translation_preserves_relative_structure(self):
        """Test that relative directory structure is preserved."""
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test suffix mode preserves structure
            result_json = tool._run(
                original_path="a/b/c/file.md",
                content="test",
                language="en",
                output_root=tmpdir,
                naming_convention="suffix"
            )
            result = json.loads(result_json)
            saved_path = Path(result["saved_path"])
            assert saved_path.name == "file.en.md"
            assert "a" in saved_path.parts and "b" in saved_path.parts and "c" in saved_path.parts
            
            # Test directory mode preserves structure
            result_json = tool._run(
                original_path="a/b/c/file.md",
                content="test",
                language="zh-CN",
                output_root=tmpdir,
                naming_convention="directory"
            )
            result = json.loads(result_json)
            saved_path = Path(result["saved_path"])
            assert saved_path.name == "file.md"
            assert "zh-CN" in saved_path.parts
            assert "a" in saved_path.parts and "b" in saved_path.parts and "c" in saved_path.parts

    def test_save_translation_error_handling(self):
        """Test error handling for file system errors."""
        tool = SaveTranslationTool()
        
        # Try to write to an invalid path (should fail gracefully)
        result_json = tool._run(
            original_path="test.md",
            content="test",
            language="en",
            output_root="/invalid/nonexistent/path/that/should/not/exist",
            naming_convention="suffix"
        )
        
        result = json.loads(result_json)
        # On some systems this might succeed (if permissions allow), 
        # but we're testing that it returns valid JSON either way
        assert "success" in result
        assert isinstance(result["success"], bool)

    def test_save_translation_updates_cache(self):
        """Test that cache metadata is updated after successful save."""
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "test-cache.json")
            
            # Save first translation
            result_json = tool.run({
                "original_path": "docs/test.md",
                "content": "# Test Content",
                "language": "en",
                "output_root": tmpdir,
                "naming_convention": "suffix",
                "cache_path": cache_path,
                "commit_hash": "abc123"
            })
            
            result = json.loads(result_json)
            assert result["success"] is True
            
            # Verify cache was created and updated
            assert Path(cache_path).exists()
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            assert cache_data["version"] == "1.0"
            assert "last_run" in cache_data
            assert len(cache_data["files"]) == 1
            
            file_entry = cache_data["files"][0]
            assert file_entry["path"] == "docs/test.md"
            assert file_entry["commit_hash"] == "abc123"
            assert "en" in file_entry["translated_languages"]
            assert "en" in file_entry["translations"]
            assert file_entry["translations"]["en"]["output_path"] == result["saved_path"]
            assert "translated_at" in file_entry["translations"]["en"]

    def test_save_translation_updates_existing_cache_entry(self):
        """Test that existing cache entries are updated correctly."""
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "test-cache.json")
            
            # Save first translation (English)
            tool.run({
                "original_path": "docs/test.md",
                "content": "# Test Content EN",
                "language": "en",
                "output_root": tmpdir,
                "naming_convention": "suffix",
                "cache_path": cache_path,
                "commit_hash": "abc123"
            })
            
            # Save second translation (Chinese) for same file
            result_json = tool.run({
                "original_path": "docs/test.md",
                "content": "# 测试内容",
                "language": "zh-CN",
                "output_root": tmpdir,
                "naming_convention": "suffix",
                "cache_path": cache_path,
                "commit_hash": "abc123"
            })
            
            result = json.loads(result_json)
            assert result["success"] is True
            
            # Verify cache has both translations for the same file
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            assert len(cache_data["files"]) == 1  # Still only one file entry
            
            file_entry = cache_data["files"][0]
            assert file_entry["path"] == "docs/test.md"
            assert set(file_entry["translated_languages"]) == {"en", "zh-CN"}
            assert "en" in file_entry["translations"]
            assert "zh-CN" in file_entry["translations"]

    def test_save_translation_handles_corrupted_cache(self):
        """Test that corrupted cache is handled gracefully."""
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "test-cache.json")
            
            # Create corrupted cache file
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write("{ invalid json content }")
            
            # Should still succeed and create new cache
            result_json = tool.run({
                "original_path": "docs/test.md",
                "content": "# Test",
                "language": "en",
                "output_root": tmpdir,
                "naming_convention": "suffix",
                "cache_path": cache_path,
                "commit_hash": "abc123"
            })
            
            result = json.loads(result_json)
            assert result["success"] is True
            
            # Verify cache was recreated
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            assert cache_data["version"] == "1.0"
            assert len(cache_data["files"]) == 1
