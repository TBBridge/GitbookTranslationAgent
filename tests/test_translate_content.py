"""Unit tests for TranslateContentTool."""

import os
import json
import pytest
from unittest.mock import Mock, patch

from src.tools.translate_content import TranslateContentTool
from src.models.markdown_models import Segment, SegmentType, SegmentMetadata, StructureInfo
from src.models.glossary_models import Glossary
from src.models.translation_models import TranslationRequest


@pytest.fixture
def mock_llm_response():
    """Mock LLM response."""
    mock_response = Mock()
    mock_response.content = """[Segment 1]
This is a test translation.

[Segment 2]
Another translated segment."""
    return mock_response


@pytest.fixture
def sample_segments():
    """Sample segments for testing."""
    return [
        {
            "type": "translatable",
            "content": "これはテストです。\n\n",
            "start_line": 0,
            "end_line": 1,
            "metadata": None
        },
        {
            "type": "protected",
            "content": "```python\ncode\n```",
            "start_line": 2,
            "end_line": 4,
            "metadata": {
                "protection_reason": "code-block",
                "link_url": None,
                "alt_text": None
            }
        },
        {
            "type": "translatable",
            "content": "別のテキスト。",
            "start_line": 5,
            "end_line": 5,
            "metadata": None
        }
    ]


@pytest.fixture
def sample_glossary():
    """Sample glossary for testing."""
    return {
        "format": "auto-detected",
        "mappings": {
            "テスト": {
                "en": "test",
                "zh-CN": "测试"
            }
        }
    }


@pytest.fixture
def sample_structure():
    """Sample structure for testing."""
    return {
        "line_breaks": [1],
        "indentation": {},
        "whitespace": {}
    }


def test_tool_initialization():
    """Test that tool initializes correctly."""
    # Set mock API key
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    tool = TranslateContentTool()
    
    assert tool.name == "translate_content"
    assert tool.llm is not None
    assert "translate" in tool.description.lower()


def test_tool_with_mock_llm(mock_llm_response, sample_segments, sample_glossary, sample_structure):
    """Test tool execution with mocked LLM."""
    # Set mock API key
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    tool = TranslateContentTool()
    
    # Mock the LLM's invoke method using patch on the instance
    from src.models.translation_models import TranslationResult
    from src.models.markdown_models import Segment, SegmentType
    
    # Create a mock that returns our mock response
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_llm_response):
        result_json = tool._run(
            segments=sample_segments,
            target_language="en",
            glossary=sample_glossary,
            structure=sample_structure
        )
        
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert "translated_segments" in result
        assert "reconstructed_content" in result
        assert len(result["translated_segments"]) == 3


def test_parse_segments():
    """Test segment parsing."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    segments_data = [
        {
            "type": "translatable",
            "content": "test",
            "start_line": 0,
            "end_line": 0,
            "metadata": None
        }
    ]
    
    segments = tool._parse_segments(segments_data)
    
    assert len(segments) == 1
    assert segments[0].type == SegmentType.TRANSLATABLE
    assert segments[0].content == "test"


def test_parse_glossary():
    """Test glossary parsing."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    glossary_data = {
        "format": "auto-detected",
        "mappings": {
            "term": {"en": "translation"}
        }
    }
    
    glossary = tool._parse_glossary(glossary_data)
    
    assert glossary.format == "auto-detected"
    assert "term" in glossary.mappings
    assert glossary.mappings["term"]["en"] == "translation"


def test_format_glossary_for_prompt():
    """Test glossary formatting for prompt."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    glossary = Glossary(
        format="auto-detected",
        mappings={
            "テスト": {"en": "test", "zh-CN": "测试"},
            "データ": {"en": "data"}
        }
    )
    
    formatted = tool._format_glossary_for_prompt(glossary, "en")
    
    assert "テスト → test" in formatted
    assert "データ → data" in formatted


def test_reconstruct_content():
    """Test content reconstruction."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    segments = [
        Segment(
            type=SegmentType.TRANSLATABLE,
            content="Hello ",
            start_line=0,
            end_line=0,
            metadata=None
        ),
        Segment(
            type=SegmentType.PROTECTED,
            content="`code`",
            start_line=0,
            end_line=0,
            metadata=SegmentMetadata(protection_reason="inline-code")
        ),
        Segment(
            type=SegmentType.TRANSLATABLE,
            content=" world",
            start_line=0,
            end_line=0,
            metadata=None
        )
    ]
    
    content = tool._reconstruct_content(segments)
    
    assert content == "Hello `code` world"


def test_error_handling():
    """Test error handling when translation fails."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    # Mock LLM to raise an exception
    with patch.object(tool.llm.__class__, 'invoke', side_effect=Exception("API Error")):
        result_json = tool._run(
            segments=[{
                "type": "translatable",
                "content": "test",
                "start_line": 0,
                "end_line": 0,
                "metadata": None
            }],
            target_language="en",
            glossary={"format": "auto-detected", "mappings": {}},
            structure={"line_breaks": [], "indentation": {}, "whitespace": {}}
        )
        
        result = json.loads(result_json)
        
        assert result["success"] is False
        assert "error" in result
        assert "API Error" in result["error"]


def test_glossary_application_in_prompt():
    """Test that glossary terms are correctly formatted and included in translation prompt."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    glossary = Glossary(
        format="auto-detected",
        mappings={
            "テスト": {"en": "test", "zh-CN": "测试"},
            "データベース": {"en": "database", "zh-CN": "数据库"},
            "API": {"en": "API", "zh-CN": "API"}
        }
    )
    
    # Test English glossary formatting
    formatted_en = tool._format_glossary_for_prompt(glossary, "en")
    assert "テスト → test" in formatted_en
    assert "データベース → database" in formatted_en
    assert "API → API" in formatted_en
    
    # Test Chinese glossary formatting
    formatted_zh = tool._format_glossary_for_prompt(glossary, "zh-CN")
    assert "テスト → 测试" in formatted_zh
    assert "データベース → 数据库" in formatted_zh
    assert "API → API" in formatted_zh


def test_glossary_with_missing_language():
    """Test glossary formatting when target language is not in mappings."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    glossary = Glossary(
        format="auto-detected",
        mappings={
            "テスト": {"en": "test"},
            "データ": {"zh-CN": "数据"}
        }
    )
    
    # Request French which is not in mappings
    formatted = tool._format_glossary_for_prompt(glossary, "fr")
    
    # Should indicate no glossary terms available for French
    assert "fr" in formatted.lower() or "no glossary" in formatted.lower()


def test_protected_region_preservation_code_blocks(mock_llm_response):
    """Test that code blocks are preserved during translation."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    segments = [
        {
            "type": "translatable",
            "content": "以下はコード例です。\n\n",
            "start_line": 0,
            "end_line": 1,
            "metadata": None
        },
        {
            "type": "protected",
            "content": "```python\ndef hello():\n    print('Hello')\n```",
            "start_line": 2,
            "end_line": 5,
            "metadata": {
                "protection_reason": "code-block",
                "link_url": None,
                "alt_text": None
            }
        },
        {
            "type": "translatable",
            "content": "\n上記のコードを実行してください。",
            "start_line": 6,
            "end_line": 6,
            "metadata": None
        }
    ]
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_llm_response):
        result_json = tool._run(
            segments=segments,
            target_language="en",
            glossary={"format": "auto-detected", "mappings": {}},
            structure={"line_breaks": [1, 5], "indentation": {}, "whitespace": {}}
        )
        
        result = json.loads(result_json)
        
        # Verify protected segment is preserved
        protected_seg = result["translated_segments"][1]
        assert protected_seg["type"] == "protected"
        assert "```python" in protected_seg["content"]
        assert "def hello():" in protected_seg["content"]
        assert protected_seg["metadata"]["protection_reason"] == "code-block"


def test_protected_region_preservation_inline_code(mock_llm_response):
    """Test that inline code is preserved during translation."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    segments = [
        {
            "type": "translatable",
            "content": "関数 ",
            "start_line": 0,
            "end_line": 0,
            "metadata": None
        },
        {
            "type": "protected",
            "content": "`print()`",
            "start_line": 0,
            "end_line": 0,
            "metadata": {
                "protection_reason": "inline-code",
                "link_url": None,
                "alt_text": None
            }
        },
        {
            "type": "translatable",
            "content": " を使用します。",
            "start_line": 0,
            "end_line": 0,
            "metadata": None
        }
    ]
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_llm_response):
        result_json = tool._run(
            segments=segments,
            target_language="en",
            glossary={"format": "auto-detected", "mappings": {}},
            structure={"line_breaks": [], "indentation": {}, "whitespace": {}}
        )
        
        result = json.loads(result_json)
        
        # Verify inline code segment is preserved
        inline_code_seg = result["translated_segments"][1]
        assert inline_code_seg["type"] == "protected"
        assert inline_code_seg["content"] == "`print()`"
        assert inline_code_seg["metadata"]["protection_reason"] == "inline-code"


def test_protected_region_preservation_urls(mock_llm_response):
    """Test that URLs in links are preserved during translation."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    segments = [
        {
            "type": "translatable",
            "content": "詳細は",
            "start_line": 0,
            "end_line": 0,
            "metadata": None
        },
        {
            "type": "protected",
            "content": "[ドキュメント](https://example.com/docs)",
            "start_line": 0,
            "end_line": 0,
            "metadata": {
                "protection_reason": "url",
                "link_url": "https://example.com/docs",
                "alt_text": None
            }
        },
        {
            "type": "translatable",
            "content": "を参照してください。",
            "start_line": 0,
            "end_line": 0,
            "metadata": None
        }
    ]
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_llm_response):
        result_json = tool._run(
            segments=segments,
            target_language="en",
            glossary={"format": "auto-detected", "mappings": {}},
            structure={"line_breaks": [], "indentation": {}, "whitespace": {}}
        )
        
        result = json.loads(result_json)
        
        # Verify URL is preserved
        url_seg = result["translated_segments"][1]
        assert url_seg["type"] == "protected"
        assert "https://example.com/docs" in url_seg["content"]
        assert url_seg["metadata"]["link_url"] == "https://example.com/docs"


def test_protected_region_preservation_yaml_frontmatter(mock_llm_response):
    """Test that YAML frontmatter is preserved during translation."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    segments = [
        {
            "type": "protected",
            "content": "---\ntitle: テスト\nauthor: 著者\n---",
            "start_line": 0,
            "end_line": 3,
            "metadata": {
                "protection_reason": "yaml",
                "link_url": None,
                "alt_text": None
            }
        },
        {
            "type": "translatable",
            "content": "\n本文です。",
            "start_line": 4,
            "end_line": 4,
            "metadata": None
        }
    ]
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_llm_response):
        result_json = tool._run(
            segments=segments,
            target_language="en",
            glossary={"format": "auto-detected", "mappings": {}},
            structure={"line_breaks": [3], "indentation": {}, "whitespace": {}}
        )
        
        result = json.loads(result_json)
        
        # Verify YAML frontmatter is preserved
        yaml_seg = result["translated_segments"][0]
        assert yaml_seg["type"] == "protected"
        assert "---" in yaml_seg["content"]
        assert "title: テスト" in yaml_seg["content"]
        assert yaml_seg["metadata"]["protection_reason"] == "yaml"


def test_protected_region_preservation_gitbook_tags(mock_llm_response):
    """Test that GitBook tags are preserved during translation."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    segments = [
        {
            "type": "protected",
            "content": "{% hint type=\"info\" %}\n重要な情報\n{% endhint %}",
            "start_line": 0,
            "end_line": 2,
            "metadata": {
                "protection_reason": "gitbook-tag",
                "link_url": None,
                "alt_text": None
            }
        }
    ]
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_llm_response):
        result_json = tool._run(
            segments=segments,
            target_language="en",
            glossary={"format": "auto-detected", "mappings": {}},
            structure={"line_breaks": [2], "indentation": {}, "whitespace": {}}
        )
        
        result = json.loads(result_json)
        
        # Verify GitBook tag is preserved
        tag_seg = result["translated_segments"][0]
        assert tag_seg["type"] == "protected"
        assert "{% hint" in tag_seg["content"]
        assert "{% endhint %}" in tag_seg["content"]
        assert tag_seg["metadata"]["protection_reason"] == "gitbook-tag"


def test_multiple_glossary_terms_in_translation():
    """Test that multiple glossary terms are correctly formatted."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    glossary = Glossary(
        format="auto-detected",
        mappings={
            "テスト": {"en": "test"},
            "データベース": {"en": "database"},
            "API": {"en": "API"},
            "ユーザー": {"en": "user"},
            "認証": {"en": "authentication"}
        }
    )
    
    formatted = tool._format_glossary_for_prompt(glossary, "en")
    
    # Verify all terms are included
    assert "テスト → test" in formatted
    assert "データベース → database" in formatted
    assert "API → API" in formatted
    assert "ユーザー → user" in formatted
    assert "認証 → authentication" in formatted


def test_empty_glossary_handling():
    """Test handling of empty glossary."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    glossary = Glossary(
        format="auto-detected",
        mappings={}
    )
    
    formatted = tool._format_glossary_for_prompt(glossary, "en")
    
    # Should indicate no glossary terms
    assert "no glossary" in formatted.lower() or "provided" in formatted.lower()


def test_structure_info_formatting():
    """Test that structure information is correctly formatted for prompt."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    structure = StructureInfo(
        line_breaks=[1, 3, 5, 7],
        indentation={0: 0, 1: 2, 2: 2, 3: 0},
        whitespace={2: "  ", 4: "    "}
    )
    
    formatted = tool._format_structure_for_prompt(structure)
    
    # Verify structure information is included
    assert "line breaks" in formatted.lower() or "Line breaks" in formatted
    assert "indentation" in formatted.lower() or "Indentation" in formatted
    assert "whitespace" in formatted.lower() or "whitespace" in formatted
