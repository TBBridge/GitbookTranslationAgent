"""Test the review translation prompt template."""

import pytest
from src.tools.review_translation import ReviewTranslationTool


def test_review_tool_initialization():
    """Test that ReviewTranslationTool initializes with prompt template and parser."""
    tool = ReviewTranslationTool()
    
    # Verify prompt template is initialized
    assert tool.prompt_template is not None
    
    # Verify output parser is initialized
    assert tool.output_parser is not None
    
    # Verify LLM is initialized
    assert tool.llm is not None


def test_format_glossary_terms_with_valid_glossary():
    """Test formatting glossary terms for the prompt."""
    tool = ReviewTranslationTool()
    
    glossary = {
        "format": "auto-detected",
        "mappings": {
            "帳票定義": {
                "en": "Template Form",
                "zh-CN": "报表定义"
            },
            "ワークフロー": {
                "en": "Workflow",
                "zh-CN": "工作流"
            }
        }
    }
    
    # Test English formatting
    result_en = tool._format_glossary_terms(glossary, "en")
    assert "帳票定義 → Template Form" in result_en
    assert "ワークフロー → Workflow" in result_en
    
    # Test Chinese formatting
    result_zh = tool._format_glossary_terms(glossary, "zh-CN")
    assert "帳票定義 → 报表定义" in result_zh
    assert "ワークフロー → 工作流" in result_zh


def test_format_glossary_terms_with_empty_glossary():
    """Test formatting with empty glossary."""
    tool = ReviewTranslationTool()
    
    # Test with empty dict
    result = tool._format_glossary_terms({}, "en")
    assert "No glossary terms provided" in result
    
    # Test with no mappings
    result = tool._format_glossary_terms({"mappings": {}}, "en")
    assert "No glossary terms provided" in result


def test_format_glossary_terms_with_missing_language():
    """Test formatting when target language is not in glossary."""
    tool = ReviewTranslationTool()
    
    glossary = {
        "mappings": {
            "帳票定義": {
                "en": "Template Form"
            }
        }
    }
    
    result = tool._format_glossary_terms(glossary, "fr")
    assert "No glossary terms available for language: fr" in result


def test_prompt_template_formatting():
    """Test that the prompt template can be formatted with all required variables."""
    tool = ReviewTranslationTool()
    
    glossary = {
        "mappings": {
            "帳票定義": {
                "en": "Template Form"
            }
        }
    }
    
    glossary_terms = tool._format_glossary_terms(glossary, "en")
    format_instructions = tool.output_parser.get_format_instructions()
    
    # Format the prompt
    formatted_prompt = tool.prompt_template.format_messages(
        target_language="en",
        glossary_terms=glossary_terms,
        format_instructions=format_instructions,
        original_content="# テスト\n\nこれはテストです。",
        translated_content="# Test\n\nThis is a test."
    )
    
    # Verify we got messages back
    assert len(formatted_prompt) == 2
    
    # Verify system message contains verification checklist
    system_message = formatted_prompt[0].content
    assert "Verification Checklist" in system_message
    assert "Format Preservation" in system_message
    assert "Completeness" in system_message
    assert "Terminology" in system_message
    assert "Links" in system_message
    assert "Style" in system_message
    
    # Verify system message contains severity guidelines
    assert "BLOCKER" in system_message
    assert "MAJOR" in system_message
    assert "MINOR" in system_message
    
    # Verify system message contains glossary terms
    assert "帳票定義 → Template Form" in system_message
    
    # Verify system message contains format instructions
    assert format_instructions in system_message
    
    # Verify user message contains content
    user_message = formatted_prompt[1].content
    assert "Original Content:" in user_message
    assert "テスト" in user_message
    assert "Translated Content:" in user_message
    assert "This is a test" in user_message


def test_output_parser_schema():
    """Test that the output parser has the correct schema."""
    tool = ReviewTranslationTool()
    
    # Get format instructions
    format_instructions = tool.output_parser.get_format_instructions()
    
    # Verify key fields are mentioned in the schema
    assert "issues" in format_instructions
    assert "approved" in format_instructions
    assert "severity" in format_instructions
    assert "category" in format_instructions
    assert "line" in format_instructions
    assert "description" in format_instructions
