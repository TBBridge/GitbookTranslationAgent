"""Property-based tests for SaveTranslationTool.

Feature: gitbook-translator, Property 15: File naming consistency
Feature: gitbook-translator, Property 16: Directory structure preservation
"""

import json
import tempfile
from pathlib import Path
from typing import Literal

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck

from src.tools.save_translation import SaveTranslationTool


# Windows reserved names that should be avoided
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

# Strategy for generating valid file paths with directory structure
@st.composite
def file_paths_with_structure(draw):
    """Generate realistic file paths with directory structure."""
    # Use alphanumeric + underscore + hyphen for safe filenames
    safe_chars = st.characters(
        whitelist_categories=('Ll', 'Lu', 'Nd'),  # lowercase, uppercase, digits
        whitelist_characters='_-'
    )
    
    def is_valid_name(name):
        """Check if name is not a Windows reserved name."""
        return name.upper() not in WINDOWS_RESERVED_NAMES
    
    # Generate 0-3 directory levels
    num_dirs = draw(st.integers(min_value=0, max_value=3))
    dirs = []
    for _ in range(num_dirs):
        dirname = draw(st.text(
            alphabet=safe_chars,
            min_size=1,
            max_size=15
        ).filter(is_valid_name))
        dirs.append(dirname)
    
    # Generate filename (without extension)
    filename = draw(st.text(
        alphabet=safe_chars,
        min_size=1,
        max_size=15
    ).filter(is_valid_name))
    
    # Combine into path
    path_parts = dirs + [f"{filename}.md"]
    return "/".join(path_parts)


# Strategy for language codes
language_codes = st.sampled_from(["en", "zh-CN", "zh-TW", "ja", "fr", "de", "es"])


class TestFileNamingConsistency:
    """Property tests for file naming consistency (Property 15)."""

    @given(
        original_path=file_paths_with_structure(),
        language=language_codes
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_suffix_naming_convention(self, original_path, language):
        """
        Property 15: File naming consistency - Suffix mode
        
        For any translated file in suffix mode, the output filename should 
        follow the pattern `<name>.<lang>.md`.
        
        **Validates: Requirements 13.1, 13.2**
        """
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_json = tool._run(
                original_path=original_path,
                content="Test content",
                language=language,
                output_root=tmpdir,
                naming_convention="suffix"
            )
            
            result = json.loads(result_json)
            assert result["success"] is True, f"Failed to save: {result.get('error')}"
            
            saved_path = Path(result["saved_path"])
            
            # Extract original filename components
            original_path_obj = Path(original_path)
            original_stem = original_path_obj.stem
            original_suffix = original_path_obj.suffix
            
            # Verify filename follows pattern: <name>.<lang>.md
            expected_filename = f"{original_stem}.{language}{original_suffix}"
            assert saved_path.name == expected_filename, \
                f"Expected filename {expected_filename}, got {saved_path.name}"
            
            # Verify file exists and is readable
            assert saved_path.exists(), f"File not created at {saved_path}"
            assert saved_path.is_file(), f"Path is not a file: {saved_path}"

    @given(
        original_path=file_paths_with_structure(),
        language=language_codes
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_directory_naming_convention(self, original_path, language):
        """
        Property 15: File naming consistency - Directory mode
        
        For any translated file in directory mode, it should be saved in 
        `/<lang>/<original-path>`.
        
        **Validates: Requirements 13.1, 13.2**
        """
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_json = tool._run(
                original_path=original_path,
                content="Test content",
                language=language,
                output_root=tmpdir,
                naming_convention="directory"
            )
            
            result = json.loads(result_json)
            assert result["success"] is True, f"Failed to save: {result.get('error')}"
            
            saved_path = Path(result["saved_path"])
            
            # Verify filename is unchanged
            original_path_obj = Path(original_path)
            assert saved_path.name == original_path_obj.name, \
                f"Filename changed: expected {original_path_obj.name}, got {saved_path.name}"
            
            # Verify language directory is in path
            assert language in saved_path.parts, \
                f"Language directory '{language}' not found in path: {saved_path}"
            
            # Verify file exists and is readable
            assert saved_path.exists(), f"File not created at {saved_path}"
            assert saved_path.is_file(), f"Path is not a file: {saved_path}"


class TestDirectoryStructurePreservation:
    """Property tests for directory structure preservation (Property 16)."""

    @given(
        original_path=file_paths_with_structure(),
        language=language_codes,
        naming_convention=st.sampled_from(["suffix", "directory"])
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_relative_directory_structure_preserved(
        self,
        original_path,
        language,
        naming_convention
    ):
        """
        Property 16: Directory structure preservation
        
        For any source file with relative directory structure, the translated 
        output should preserve that structure relative to the output root.
        
        **Validates: Requirements 13.4**
        """
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_json = tool._run(
                original_path=original_path,
                content="Test content",
                language=language,
                output_root=tmpdir,
                naming_convention=naming_convention
            )
            
            result = json.loads(result_json)
            assert result["success"] is True, f"Failed to save: {result.get('error')}"
            
            saved_path = Path(result["saved_path"])
            original_path_obj = Path(original_path)
            
            # Extract directory structure from original path
            original_dirs = original_path_obj.parent.parts
            
            # Verify directory structure is preserved
            saved_path_parts = saved_path.parts
            
            if naming_convention == "suffix":
                # In suffix mode, directory structure should be preserved as-is
                # Check that all original directories appear in the saved path
                for original_dir in original_dirs:
                    assert original_dir in saved_path_parts, \
                        f"Directory '{original_dir}' not preserved in path: {saved_path}"
            else:  # directory mode
                # In directory mode, structure should be preserved after language dir
                # Find where language directory is
                lang_index = None
                for i, part in enumerate(saved_path_parts):
                    if part == language:
                        lang_index = i
                        break
                
                assert lang_index is not None, \
                    f"Language directory '{language}' not found in path: {saved_path}"
                
                # Check that original directories appear after language directory
                saved_dirs_after_lang = saved_path_parts[lang_index + 1:-1]  # Exclude filename
                
                for original_dir in original_dirs:
                    assert original_dir in saved_dirs_after_lang, \
                        f"Directory '{original_dir}' not preserved after language dir in: {saved_path}"
            
            # Verify file exists
            assert saved_path.exists(), f"File not created at {saved_path}"

    @given(
        original_path=file_paths_with_structure(),
        language=language_codes
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_nested_directory_creation(self, original_path, language):
        """
        Property 16: Directory structure preservation - Nested directories
        
        For any source file with nested directory structure, all intermediate 
        directories should be created automatically.
        
        **Validates: Requirements 13.4**
        """
        tool = SaveTranslationTool()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result_json = tool._run(
                original_path=original_path,
                content="Test content",
                language=language,
                output_root=tmpdir,
                naming_convention="suffix"
            )
            
            result = json.loads(result_json)
            assert result["success"] is True, f"Failed to save: {result.get('error')}"
            
            saved_path = Path(result["saved_path"])
            
            # Verify all parent directories exist
            current = saved_path.parent
            while current != Path(tmpdir):
                assert current.exists(), f"Parent directory not created: {current}"
                assert current.is_dir(), f"Path is not a directory: {current}"
                current = current.parent
