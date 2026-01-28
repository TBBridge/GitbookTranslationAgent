"""Unit tests for LoadGlossaryTool."""

import json
import csv
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.tools.load_glossary import LoadGlossaryTool
from src.models.glossary_models import Glossary


@pytest.fixture
def glossary_tool():
    """Create a LoadGlossaryTool instance."""
    return LoadGlossaryTool()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestLoadGlossaryToolJSON:
    """Tests for JSON glossary loading."""

    def test_load_json_glossary_with_terms_array(self, glossary_tool, temp_dir):
        """Test loading JSON glossary with terms array format."""
        glossary_data = {
            "terms": [
                {
                    "ja": "帳票定義",
                    "en": "Template Form",
                    "zh-CN": "报表定义",
                    "zh-TW": "表單定義"
                },
                {
                    "ja": "ユーザー",
                    "en": "User",
                    "zh-CN": "用户"
                }
            ]
        }
        
        glossary_path = temp_dir / "glossary.json"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False)
        
        glossary = glossary_tool.load_glossary(str(glossary_path))
        
        assert glossary.format == "auto-detected"
        assert len(glossary.mappings) == 2
        assert "帳票定義" in glossary.mappings
        assert glossary.mappings["帳票定義"]["en"] == "Template Form"
        assert glossary.mappings["帳票定義"]["zh-CN"] == "报表定义"
        assert glossary.mappings["ユーザー"]["en"] == "User"

    def test_load_json_glossary_with_flat_format(self, glossary_tool, temp_dir):
        """Test loading JSON glossary with flat format."""
        glossary_data = {
            "帳票定義": {
                "en": "Template Form",
                "zh-CN": "报表定义"
            },
            "ユーザー": {
                "en": "User",
                "zh-CN": "用户"
            }
        }
        
        glossary_path = temp_dir / "glossary.json"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False)
        
        glossary = glossary_tool.load_glossary(str(glossary_path))
        
        assert glossary.format == "auto-detected"
        assert len(glossary.mappings) == 2
        assert glossary.mappings["帳票定義"]["en"] == "Template Form"
        assert glossary.mappings["ユーザー"]["en"] == "User"

    def test_load_json_glossary_with_extension(self, glossary_tool, temp_dir):
        """Test that .json extension is recognized."""
        glossary_data = {
            "terms": [
                {
                    "ja": "テスト",
                    "en": "Test"
                }
            ]
        }
        
        glossary_path = temp_dir / "glossary.json"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False)
        
        glossary = glossary_tool.load_glossary(str(glossary_path))
        
        assert glossary.format == "auto-detected"
        assert "テスト" in glossary.mappings


class TestLoadGlossaryToolCSV:
    """Tests for CSV glossary loading."""

    def test_load_csv_glossary(self, glossary_tool, temp_dir):
        """Test loading CSV glossary."""
        glossary_path = temp_dir / "glossary.csv"
        
        with open(glossary_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ja', 'en', 'zh-CN'])
            writer.writerow(['帳票定義', 'Template Form', '报表定义'])
            writer.writerow(['ユーザー', 'User', '用户'])
        
        glossary = glossary_tool.load_glossary(str(glossary_path))
        
        assert glossary.format == "auto-detected"
        assert len(glossary.mappings) == 2
        assert glossary.mappings["帳票定義"]["en"] == "Template Form"
        assert glossary.mappings["帳票定義"]["zh-CN"] == "报表定义"
        assert glossary.mappings["ユーザー"]["en"] == "User"

    def test_load_csv_glossary_with_extension(self, glossary_tool, temp_dir):
        """Test that .csv extension is recognized."""
        glossary_path = temp_dir / "glossary.csv"
        
        with open(glossary_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ja', 'en'])
            writer.writerow(['テスト', 'Test'])
        
        glossary = glossary_tool.load_glossary(str(glossary_path))
        
        assert glossary.format == "auto-detected"
        assert "テスト" in glossary.mappings


class TestLoadGlossaryToolAutoDetect:
    """Tests for auto-detection of glossary format."""

    def test_auto_detect_json_format(self, glossary_tool, temp_dir):
        """Test auto-detection of JSON format without extension."""
        glossary_data = {
            "terms": [
                {
                    "ja": "テスト",
                    "en": "Test"
                }
            ]
        }
        
        glossary_path = temp_dir / "glossary"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False)
        
        glossary = glossary_tool.load_glossary(str(glossary_path))
        
        assert glossary.format == "auto-detected"
        assert "テスト" in glossary.mappings

    def test_auto_detect_csv_format(self, glossary_tool, temp_dir):
        """Test auto-detection of CSV format without extension."""
        glossary_path = temp_dir / "glossary"
        
        with open(glossary_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ja', 'en'])
            writer.writerow(['テスト', 'Test'])
        
        glossary = glossary_tool.load_glossary(str(glossary_path))
        
        assert glossary.format == "auto-detected"
        assert "テスト" in glossary.mappings


class TestLoadGlossaryToolErrors:
    """Tests for error handling."""

    def test_file_not_found(self, glossary_tool):
        """Test error when glossary file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            glossary_tool.load_glossary("/nonexistent/path/glossary.json")

    def test_invalid_json_format(self, glossary_tool, temp_dir):
        """Test error with invalid JSON."""
        glossary_path = temp_dir / "glossary.json"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            f.write("{ invalid json }")
        
        with pytest.raises(Exception):
            glossary_tool.load_glossary(str(glossary_path))

    def test_empty_csv_file(self, glossary_tool, temp_dir):
        """Test error with empty CSV file."""
        glossary_path = temp_dir / "glossary.csv"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            f.write("")
        
        with pytest.raises(ValueError):
            glossary_tool.load_glossary(str(glossary_path))


class TestLoadGlossaryToolRun:
    """Tests for the _run method."""

    def test_run_with_valid_glossary(self, glossary_tool, temp_dir):
        """Test _run method with valid glossary."""
        glossary_data = {
            "terms": [
                {
                    "ja": "テスト",
                    "en": "Test"
                }
            ]
        }
        
        glossary_path = temp_dir / "glossary.json"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False)
        
        result = glossary_tool._run(glossary_path=str(glossary_path))
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["format"] == "auto-detected"
        assert result_data["term_count"] == 1

    def test_run_with_missing_file(self, glossary_tool):
        """Test _run method with missing file."""
        result = glossary_tool._run(glossary_path="/nonexistent/glossary.json")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "not found" in result_data["error"].lower()

    def test_run_with_invalid_format(self, glossary_tool, temp_dir):
        """Test _run method with invalid format."""
        glossary_path = temp_dir / "glossary.txt"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            f.write("invalid format")
        
        result = glossary_tool._run(glossary_path=str(glossary_path))
        result_data = json.loads(result)
        
        assert result_data["success"] is False


class TestLoadGlossaryToolMultiLanguage:
    """Tests for multi-language glossary support."""

    def test_multiple_language_mappings(self, glossary_tool, temp_dir):
        """Test glossary with multiple language mappings."""
        glossary_data = {
            "terms": [
                {
                    "ja": "帳票定義",
                    "en": "Template Form",
                    "zh-CN": "报表定义",
                    "zh-TW": "表單定義",
                    "ko": "템플릿 양식"
                }
            ]
        }
        
        glossary_path = temp_dir / "glossary.json"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False)
        
        glossary = glossary_tool.load_glossary(str(glossary_path))
        
        assert len(glossary.mappings["帳票定義"]) == 4
        assert glossary.mappings["帳票定義"]["en"] == "Template Form"
        assert glossary.mappings["帳票定義"]["zh-CN"] == "报表定义"
        assert glossary.mappings["帳票定義"]["zh-TW"] == "表單定義"
        assert glossary.mappings["帳票定義"]["ko"] == "템플릿 양식"

    def test_partial_language_mappings(self, glossary_tool, temp_dir):
        """Test glossary where not all terms have all languages."""
        glossary_data = {
            "terms": [
                {
                    "ja": "帳票定義",
                    "en": "Template Form",
                    "zh-CN": "报表定义"
                },
                {
                    "ja": "ユーザー",
                    "en": "User"
                }
            ]
        }
        
        glossary_path = temp_dir / "glossary.json"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False)
        
        glossary = glossary_tool.load_glossary(str(glossary_path))
        
        assert len(glossary.mappings["帳票定義"]) == 2
        assert len(glossary.mappings["ユーザー"]) == 1
        assert "zh-CN" not in glossary.mappings["ユーザー"]
