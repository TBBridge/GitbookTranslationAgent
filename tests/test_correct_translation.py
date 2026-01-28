"""Unit tests for CorrectTranslationTool.

Tests the correction functionality including:
- Sending correction requests to LLM
- Parsing corrected content
- Validating corrections address issues

Requirements: 12.2, 12.3
"""

import json
import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import AIMessage

from src.tools.correct_translation import CorrectTranslationTool


@pytest.fixture
def correction_tool():
    """Create a CorrectTranslationTool instance for testing."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        tool = CorrectTranslationTool()
        return tool


def test_run_with_no_issues(correction_tool):
    """Test that _run returns original content when no issues are provided.
    
    Requirements: 12.2
    """
    content = "This is translated content."
    issues = []
    target_language = "en"
    
    result_json = correction_tool._run(
        content=content,
        issues=issues,
        target_language=target_language
    )
    
    result = json.loads(result_json)
    
    assert result["success"] is True
    assert result["corrected_content"] == content
    assert "No issues to correct" in result["message"]


def test_run_with_blocker_issues(correction_tool):
    """Test that _run corrects content with BLOCKER issues.
    
    Requirements: 12.2, 12.3
    """
    content = "This is translated content with [broken link](wrong-url)."
    issues = [
        {
            "severity": "BLOCKER",
            "category": "links",
            "line": 1,
            "description": "Link URL was modified during translation",
            "suggestion": "Restore original URL: correct-url.md"
        }
    ]
    target_language = "en"
    
    # Mock the LLM response
    mock_response = AIMessage(
        content="This is translated content with [broken link](correct-url.md)."
    )
    
    with patch.object(correction_tool.llm.__class__, 'invoke', return_value=mock_response):
        result_json = correction_tool._run(
            content=content,
            issues=issues,
            target_language=target_language
        )
        
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert "correct-url.md" in result["corrected_content"]
        assert result["validation"]["content_changed"] is True
        assert result["validation"]["blocker_issues"] == 1


def test_run_with_major_issues(correction_tool):
    """Test that _run corrects content with MAJOR issues.
    
    Requirements: 12.2, 12.3
    """
    content = "これは翻訳されたコンテンツです。"  # Untranslated Japanese
    issues = [
        {
            "severity": "MAJOR",
            "category": "completeness",
            "line": 1,
            "description": "Japanese text was not translated",
            "suggestion": "Translate the Japanese text to English"
        }
    ]
    target_language = "en"
    
    # Mock the LLM response
    mock_response = AIMessage(
        content="This is translated content."
    )
    
    with patch.object(correction_tool.llm.__class__, 'invoke', return_value=mock_response):
        result_json = correction_tool._run(
            content=content,
            issues=issues,
            target_language=target_language
        )
        
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert result["validation"]["content_changed"] is True
        assert result["validation"]["major_issues"] == 1


def test_run_with_multiple_issues(correction_tool):
    """Test that _run handles multiple issues correctly.
    
    Requirements: 12.2, 12.3
    """
    content = """# Title
    
これは翻訳されていないテキストです。

[Link](wrong-url.md)
"""
    issues = [
        {
            "severity": "BLOCKER",
            "category": "links",
            "line": 5,
            "description": "Link URL was modified",
            "suggestion": "Restore original URL: correct-url.md"
        },
        {
            "severity": "MAJOR",
            "category": "completeness",
            "line": 3,
            "description": "Japanese text not translated",
            "suggestion": "Translate to English"
        }
    ]
    target_language = "en"
    
    # Mock the LLM response
    mock_response = AIMessage(
        content="""# Title
    
This is translated text.

[Link](correct-url.md)
"""
    )
    
    with patch.object(correction_tool.llm.__class__, 'invoke', return_value=mock_response):
        result_json = correction_tool._run(
            content=content,
            issues=issues,
            target_language=target_language
        )
        
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert result["validation"]["content_changed"] is True
        assert result["validation"]["blocker_issues"] == 1
        assert result["validation"]["major_issues"] == 1
        assert result["validation"]["issues_count"] == 2


def test_run_error_handling(correction_tool):
    """Test that _run handles LLM errors gracefully.
    
    Requirements: 12.2
    """
    content = "This is translated content."
    issues = [
        {
            "severity": "MAJOR",
            "category": "style",
            "line": 1,
            "description": "Improve phrasing",
            "suggestion": "Use more formal language"
        }
    ]
    target_language = "en"
    
    # Mock the LLM to raise an exception
    with patch.object(correction_tool.llm.__class__, 'invoke', side_effect=Exception("API Error")):
        result_json = correction_tool._run(
            content=content,
            issues=issues,
            target_language=target_language
        )
        
        result = json.loads(result_json)
        
        assert result["success"] is False
        assert result["corrected_content"] == content  # Returns original on error
        assert "Correction failed" in result["error"]


def test_format_issues_for_prompt(correction_tool):
    """Test that issues are formatted correctly for the prompt.
    
    Requirements: 12.2
    """
    issues = [
        {
            "severity": "BLOCKER",
            "category": "format",
            "line": 5,
            "description": "Code block was modified",
            "suggestion": "Restore original code block"
        },
        {
            "severity": "MAJOR",
            "category": "terminology",
            "line": 10,
            "description": "Glossary term not used",
            "suggestion": "Use 'Template Form' instead of 'Form Template'"
        }
    ]
    
    formatted = correction_tool._format_issues_for_prompt(issues)
    
    assert "Issue 1 [BLOCKER - format]" in formatted
    assert "Line 5" in formatted
    assert "Code block was modified" in formatted
    assert "Restore original code block" in formatted
    
    assert "Issue 2 [MAJOR - terminology]" in formatted
    assert "Line 10" in formatted
    assert "Glossary term not used" in formatted


def test_validate_corrections_with_changes(correction_tool):
    """Test validation when corrections are made.
    
    Requirements: 12.3
    """
    original = "Original content"
    corrected = "Corrected content"
    issues = [
        {
            "severity": "BLOCKER",
            "category": "format",
            "line": 1,
            "description": "Format issue"
        }
    ]
    
    validation = correction_tool._validate_corrections(
        original_content=original,
        corrected_content=corrected,
        issues=issues
    )
    
    assert validation["content_changed"] is True
    assert validation["issues_count"] == 1
    assert validation["blocker_issues"] == 1


def test_validate_corrections_no_changes(correction_tool):
    """Test validation when no corrections are made despite issues.
    
    Requirements: 12.3
    """
    content = "Same content"
    issues = [
        {
            "severity": "MINOR",
            "category": "style",
            "line": 1,
            "description": "Style issue"
        }
    ]
    
    validation = correction_tool._validate_corrections(
        original_content=content,
        corrected_content=content,
        issues=issues
    )
    
    assert validation["content_changed"] is False
    assert validation["issues_count"] == 1
    assert any("unchanged despite issues" in note for note in validation["validation_notes"])


def test_run_preserves_format(correction_tool):
    """Test that _run preserves formatting during correction.
    
    Requirements: 12.2
    """
    content = """# Title

Paragraph with **bold** and *italic*.

```python
code block
```

- List item 1
- List item 2
"""
    issues = [
        {
            "severity": "MINOR",
            "category": "style",
            "line": 3,
            "description": "Improve phrasing",
            "suggestion": "Use more formal language"
        }
    ]
    target_language = "en"
    
    # Mock the LLM to return content with preserved formatting
    mock_response = AIMessage(content=content)
    
    with patch.object(correction_tool.llm.__class__, 'invoke', return_value=mock_response):
        result_json = correction_tool._run(
            content=content,
            issues=issues,
            target_language=target_language
        )
        
        result = json.loads(result_json)
        
        assert result["success"] is True
        # Verify formatting elements are preserved
        assert "# Title" in result["corrected_content"]
        assert "**bold**" in result["corrected_content"]
        assert "*italic*" in result["corrected_content"]
        assert "```python" in result["corrected_content"]
        assert "- List item" in result["corrected_content"]
