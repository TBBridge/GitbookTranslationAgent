"""Test the ReviewTranslationTool _run method."""

import json
import pytest
from unittest.mock import Mock, MagicMock
from langchain_core.messages import AIMessage

from src.tools.review_translation import ReviewTranslationTool


@pytest.fixture
def review_tool():
    """Create a ReviewTranslationTool instance with mocked LLM."""
    tool = ReviewTranslationTool()
    # Replace the LLM with a mock
    tool.llm = MagicMock()
    return tool


@pytest.fixture
def sample_glossary():
    """Sample glossary for testing."""
    return {
        "format": "auto-detected",
        "mappings": {
            "帳票定義": {
                "en": "Template Form",
                "zh-CN": "报表定义"
            }
        }
    }


def test_run_with_no_issues(review_tool, sample_glossary):
    """Test _run method when LLM returns no issues."""
    # Mock LLM response with no issues
    mock_response = AIMessage(content='{"issues": [], "approved": true}')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="# テスト\n\nこれはテストです。",
        translated_content="# Test\n\nThis is a test.",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    assert result["approved"] is True
    assert len(result["issues"]) == 0


def test_run_with_minor_issues(review_tool, sample_glossary):
    """Test _run method when LLM returns MINOR issues."""
    # Mock LLM response with MINOR issues
    mock_response = AIMessage(content='''{
        "issues": [
            {
                "severity": "MINOR",
                "category": "style",
                "line": 3,
                "column": 5,
                "description": "Consider using more formal language",
                "suggestion": "Use 'This is an examination' instead"
            }
        ],
        "approved": true
    }''')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="# テスト\n\nこれはテストです。",
        translated_content="# Test\n\nThis is a test.",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # MINOR issues should not prevent approval
    assert result["approved"] is True
    assert len(result["issues"]) == 1
    assert result["issues"][0]["severity"] == "MINOR"
    assert result["issues"][0]["category"] == "style"
    assert result["issues"][0]["line"] == 3


def test_run_with_major_issues(review_tool, sample_glossary):
    """Test _run method when LLM returns MAJOR issues."""
    # Mock LLM response with MAJOR issues
    mock_response = AIMessage(content='''{
        "issues": [
            {
                "severity": "MAJOR",
                "category": "terminology",
                "line": 5,
                "column": null,
                "description": "Glossary term not used correctly",
                "suggestion": "Use 'Template Form' instead of 'Form Template'"
            }
        ],
        "approved": false
    }''')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="# テスト\n\n帳票定義について",
        translated_content="# Test\n\nAbout Form Template",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # MAJOR issues should prevent approval
    assert result["approved"] is False
    assert len(result["issues"]) == 1
    assert result["issues"][0]["severity"] == "MAJOR"
    assert result["issues"][0]["category"] == "terminology"


def test_run_with_blocker_issues(review_tool, sample_glossary):
    """Test _run method when LLM returns BLOCKER issues."""
    # Mock LLM response with BLOCKER issues
    mock_response = AIMessage(content='''{
        "issues": [
            {
                "severity": "BLOCKER",
                "category": "format",
                "line": 1,
                "column": null,
                "description": "Code block formatting is broken",
                "suggestion": "Restore the original code block markers"
            }
        ],
        "approved": false
    }''')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="```python\nprint('hello')\n```",
        translated_content="python\nprint('hello')",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # BLOCKER issues should prevent approval
    assert result["approved"] is False
    assert len(result["issues"]) == 1
    assert result["issues"][0]["severity"] == "BLOCKER"
    assert result["issues"][0]["category"] == "format"


def test_run_overrides_approval_with_blocker(review_tool, sample_glossary):
    """Test that _run overrides approval=true when BLOCKER issues exist."""
    # Mock LLM response where LLM incorrectly sets approved=true with BLOCKER
    mock_response = AIMessage(content='''{
        "issues": [
            {
                "severity": "BLOCKER",
                "category": "links",
                "line": 10,
                "column": null,
                "description": "Link URL was modified",
                "suggestion": "Restore original URL"
            }
        ],
        "approved": true
    }''')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="[リンク](https://example.com)",
        translated_content="[Link](https://example.org)",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # Should override to approved=false due to BLOCKER
    assert result["approved"] is False
    assert len(result["issues"]) == 1
    assert result["issues"][0]["severity"] == "BLOCKER"


def test_run_with_multiple_issues(review_tool, sample_glossary):
    """Test _run method with multiple issues of different severities."""
    # Mock LLM response with multiple issues
    mock_response = AIMessage(content='''{
        "issues": [
            {
                "severity": "MAJOR",
                "category": "completeness",
                "line": 5,
                "column": null,
                "description": "Untranslated Japanese text found",
                "suggestion": "Translate the remaining Japanese text"
            },
            {
                "severity": "MINOR",
                "category": "style",
                "line": 8,
                "column": 10,
                "description": "Informal tone detected",
                "suggestion": "Use more formal language"
            }
        ],
        "approved": false
    }''')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="# テスト\n\nこれはテストです。\n\nもっとテキスト。",
        translated_content="# Test\n\nThis is a test.\n\nもっとテキスト。",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # MAJOR issues should prevent approval
    assert result["approved"] is False
    assert len(result["issues"]) == 2
    assert result["issues"][0]["severity"] == "MAJOR"
    assert result["issues"][1]["severity"] == "MINOR"


def test_run_with_malformed_json_response(review_tool, sample_glossary):
    """Test _run method when LLM returns JSON with extra text."""
    # Mock LLM response with extra text around JSON
    mock_response = AIMessage(content='''Here is the review result:

{
    "issues": [],
    "approved": true
}

The translation looks good!''')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="# テスト",
        translated_content="# Test",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # Should still parse successfully
    assert result["approved"] is True
    assert len(result["issues"]) == 0


def test_run_with_llm_error(review_tool, sample_glossary):
    """Test _run method when LLM raises an error."""
    # Mock LLM to raise an exception
    review_tool.llm.invoke.side_effect = Exception("API timeout")
    
    result_str = review_tool._run(
        original_content="# テスト",
        translated_content="# Test",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # Should return error as BLOCKER issue
    assert result["approved"] is False
    assert len(result["issues"]) == 1
    assert result["issues"][0]["severity"] == "BLOCKER"
    assert "API timeout" in result["issues"][0]["description"]


def test_run_preserves_unicode_in_output(review_tool, sample_glossary):
    """Test that _run preserves Unicode characters in JSON output."""
    # Mock LLM response with Unicode characters
    mock_response = AIMessage(content='''{
        "issues": [
            {
                "severity": "MINOR",
                "category": "style",
                "line": 1,
                "column": null,
                "description": "日本語の文字が残っています",
                "suggestion": "翻訳してください"
            }
        ],
        "approved": false
    }''')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="# テスト",
        translated_content="# Test",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # Unicode should be preserved
    assert "日本語" in result["issues"][0]["description"]
    assert "翻訳" in result["issues"][0]["suggestion"]


def test_run_reclassifies_incorrect_severity(review_tool, sample_glossary):
    """Test that _run reclassifies issues when LLM provides incorrect severity."""
    # Mock LLM response where LLM incorrectly classifies a structural issue as MINOR
    mock_response = AIMessage(content='''{
        "issues": [
            {
                "severity": "MINOR",
                "category": "format",
                "line": 5,
                "column": null,
                "description": "Table structure is broken and columns are misaligned",
                "suggestion": "Fix the table structure"
            }
        ],
        "approved": true
    }''')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="| A | B |\n|---|---|\n| 1 | 2 |",
        translated_content="| A | B\n|---|\n| 1 | 2 |",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # Should reclassify to BLOCKER based on classification rules
    assert result["issues"][0]["severity"] == "BLOCKER"
    # Should override approval to false due to BLOCKER
    assert result["approved"] is False


def test_run_reclassifies_glossary_violation(review_tool, sample_glossary):
    """Test that _run reclassifies glossary violations to MAJOR."""
    # Mock LLM response where LLM incorrectly classifies glossary violation as MINOR
    mock_response = AIMessage(content='''{
        "issues": [
            {
                "severity": "MINOR",
                "category": "terminology",
                "line": 3,
                "column": null,
                "description": "Glossary term not used correctly",
                "suggestion": "Use the glossary term"
            }
        ],
        "approved": true
    }''')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="帳票定義について",
        translated_content="About Form Template",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # Should reclassify to MAJOR based on classification rules
    assert result["issues"][0]["severity"] == "MAJOR"
    # Should override approval to false due to MAJOR
    assert result["approved"] is False


def test_run_reclassifies_link_corruption(review_tool, sample_glossary):
    """Test that _run reclassifies link corruption to BLOCKER."""
    # Mock LLM response where LLM incorrectly classifies link corruption as MAJOR
    mock_response = AIMessage(content='''{
        "issues": [
            {
                "severity": "MAJOR",
                "category": "links",
                "line": 1,
                "column": null,
                "description": "Link URL was modified from original",
                "suggestion": "Restore the original URL"
            }
        ],
        "approved": false
    }''')
    review_tool.llm.invoke.return_value = mock_response
    
    result_str = review_tool._run(
        original_content="[リンク](https://example.com)",
        translated_content="[Link](https://example.org)",
        target_language="en",
        glossary=sample_glossary
    )
    
    result = json.loads(result_str)
    # Should reclassify to BLOCKER based on classification rules
    assert result["issues"][0]["severity"] == "BLOCKER"
    assert result["approved"] is False
