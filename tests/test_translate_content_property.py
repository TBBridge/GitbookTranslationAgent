"""Property-based tests for TranslateContentTool.

Feature: gitbook-translator
Tests for Property 8: Japanese-only translation
"""

import os
import json
import re
from unittest.mock import Mock, patch
from hypothesis import given, settings, strategies as st, assume

from src.tools.translate_content import TranslateContentTool
from src.models.markdown_models import Segment, SegmentType, StructureInfo
from src.models.glossary_models import Glossary
from src.models.translation_models import TranslationRequest


# Strategies for generating text content
english_text_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?;:-',
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())

# Japanese text strategy - using Unicode ranges for Hiragana, Katakana, and Kanji
japanese_text_strategy = st.text(
    alphabet='あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん'
            'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン'
            '漢字文字テスト',
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())

# Mixed language strategy
mixed_text_strategy = st.one_of(
    english_text_strategy,
    japanese_text_strategy,
    st.just("Hello こんにちは World"),
    st.just("テスト test 123"),
    st.just("English and 日本語 mixed"),
)


def has_japanese_characters(text: str) -> bool:
    """Check if text contains Japanese characters."""
    # Unicode ranges for Japanese:
    # Hiragana: U+3040-U+309F
    # Katakana: U+30A0-U+30FF
    # Kanji: U+4E00-U+9FFF
    japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]'
    return bool(re.search(japanese_pattern, text))


def extract_japanese_portions(text: str) -> list:
    """Extract all Japanese character sequences from text."""
    japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+'
    return re.findall(japanese_pattern, text)


def extract_non_japanese_portions(text: str) -> list:
    """Extract all non-Japanese character sequences from text."""
    # Split by Japanese characters and filter out empty strings
    non_japanese_pattern = r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+'
    portions = re.findall(non_japanese_pattern, text)
    # Only keep portions that have non-whitespace content
    return [p for p in portions if p and not p.isspace()]


@given(
    english_text=english_text_strategy,
    japanese_text=japanese_text_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_japanese_only_translation_mixed_text(english_text: str, japanese_text: str):
    """
    Property 8: Japanese-only translation
    
    For any text segment containing both Japanese and non-Japanese text,
    only portions containing Japanese characters should be translated,
    while non-Japanese text should remain unchanged.
    
    Validates: Requirements 7.1, 7.2, 7.3, 7.4
    
    Feature: gitbook-translator, Property 8: Japanese-only translation
    """
    # Create mixed content
    mixed_content = f"{english_text} {japanese_text} {english_text}"
    
    # Create segments
    segments = [
        {
            "type": "translatable",
            "content": mixed_content,
            "start_line": 0,
            "end_line": 0,
            "metadata": None
        }
    ]
    
    glossary = {
        "format": "auto-detected",
        "mappings": {}
    }
    
    structure = {
        "line_breaks": [],
        "indentation": {},
        "whitespace": {}
    }
    
    # Mock LLM response that simulates translation
    # The mock should translate Japanese portions but keep English unchanged
    mock_response = Mock()
    
    # Create a mock translation that keeps English but changes Japanese
    # This simulates what the LLM should do
    translated_content = mixed_content.replace(japanese_text, "[TRANSLATED]")
    mock_response.content = f"[Segment 1]\n{translated_content}"
    
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_response):
        result = tool.translate(TranslationRequest(
            segments=[
                Segment(
                    type=SegmentType.TRANSLATABLE,
                    content=mixed_content,
                    start_line=0,
                    end_line=0,
                    metadata=None
                )
            ],
            target_language="en",
            glossary=Glossary(format="auto-detected", mappings={}),
            structure=StructureInfo(line_breaks=[], indentation={}, whitespace={})
        ))
        
        # Verify that English portions are preserved
        assert english_text in result.reconstructed_content
        
        # Verify that the structure is maintained
        assert result.reconstructed_content is not None
        assert len(result.translated_segments) > 0


@given(
    english_only=english_text_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_japanese_only_translation_english_only(english_only: str):
    """
    Property 8: Japanese-only translation
    
    For any text segment containing only non-Japanese text,
    the text should remain unchanged after translation.
    
    Validates: Requirements 7.1, 7.3
    
    Feature: gitbook-translator, Property 8: Japanese-only translation
    """
    # Assume text has no Japanese characters
    assume(not has_japanese_characters(english_only))
    
    segments = [
        {
            "type": "translatable",
            "content": english_only,
            "start_line": 0,
            "end_line": 0,
            "metadata": None
        }
    ]
    
    glossary = {
        "format": "auto-detected",
        "mappings": {}
    }
    
    structure = {
        "line_breaks": [],
        "indentation": {},
        "whitespace": {}
    }
    
    # Mock LLM response that keeps English text unchanged
    mock_response = Mock()
    mock_response.content = f"[Segment 1]\n{english_only}"
    
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_response):
        result = tool.translate(TranslationRequest(
            segments=[
                Segment(
                    type=SegmentType.TRANSLATABLE,
                    content=english_only,
                    start_line=0,
                    end_line=0,
                    metadata=None
                )
            ],
            target_language="en",
            glossary=Glossary(format="auto-detected", mappings={}),
            structure=StructureInfo(line_breaks=[], indentation={}, whitespace={})
        ))
        
        # English-only text should be preserved (allowing for whitespace normalization)
        assert english_only.strip() in result.reconstructed_content.strip()


@given(
    japanese_only=japanese_text_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_japanese_only_translation_japanese_only(japanese_only: str):
    """
    Property 8: Japanese-only translation
    
    For any text segment containing only Japanese text,
    the text should be translated (changed).
    
    Validates: Requirements 7.1, 7.2
    
    Feature: gitbook-translator, Property 8: Japanese-only translation
    """
    # Assume text has Japanese characters
    assume(has_japanese_characters(japanese_only))
    
    segments = [
        {
            "type": "translatable",
            "content": japanese_only,
            "start_line": 0,
            "end_line": 0,
            "metadata": None
        }
    ]
    
    glossary = {
        "format": "auto-detected",
        "mappings": {}
    }
    
    structure = {
        "line_breaks": [],
        "indentation": {},
        "whitespace": {}
    }
    
    # Mock LLM response that translates Japanese text
    mock_response = Mock()
    translated_text = "[TRANSLATED_" + japanese_only[:10] + "]"
    mock_response.content = f"[Segment 1]\n{translated_text}"
    
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_response):
        result = tool.translate(TranslationRequest(
            segments=[
                Segment(
                    type=SegmentType.TRANSLATABLE,
                    content=japanese_only,
                    start_line=0,
                    end_line=0,
                    metadata=None
                )
            ],
            target_language="en",
            glossary=Glossary(format="auto-detected", mappings={}),
            structure=StructureInfo(line_breaks=[], indentation={}, whitespace={})
        ))
        
        # Result should contain translated content
        assert result.reconstructed_content is not None
        assert len(result.translated_segments) > 0


@given(
    text_parts=st.lists(
        st.one_of(english_text_strategy, japanese_text_strategy),
        min_size=2,
        max_size=5
    )
)
@settings(max_examples=100, deadline=None)
def test_property_japanese_only_translation_preserves_non_japanese_structure(text_parts: list):
    """
    Property 8: Japanese-only translation
    
    For any text with multiple parts (some Japanese, some not),
    the non-Japanese portions should be present in the result.
    
    Validates: Requirements 7.1, 7.3, 7.4
    
    Feature: gitbook-translator, Property 8: Japanese-only translation
    """
    # Create content with multiple parts
    content = " ".join(text_parts)
    
    # Extract non-Japanese portions (without leading/trailing whitespace)
    non_japanese_portions = [p.strip() for p in extract_non_japanese_portions(content) if p.strip()]
    
    # If there are no non-Japanese portions, skip this test
    assume(len(non_japanese_portions) > 0)
    
    segments = [
        {
            "type": "translatable",
            "content": content,
            "start_line": 0,
            "end_line": 0,
            "metadata": None
        }
    ]
    
    glossary = {
        "format": "auto-detected",
        "mappings": {}
    }
    
    structure = {
        "line_breaks": [],
        "indentation": {},
        "whitespace": {}
    }
    
    # Mock LLM response that preserves non-Japanese text
    mock_response = Mock()
    # Simulate translation by replacing Japanese with [TRANSLATED]
    translated_content = content
    for jp_portion in extract_japanese_portions(content):
        translated_content = translated_content.replace(jp_portion, "[TRANSLATED]", 1)
    
    mock_response.content = f"[Segment 1]\n{translated_content}"
    
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_response):
        result = tool.translate(TranslationRequest(
            segments=[
                Segment(
                    type=SegmentType.TRANSLATABLE,
                    content=content,
                    start_line=0,
                    end_line=0,
                    metadata=None
                )
            ],
            target_language="en",
            glossary=Glossary(format="auto-detected", mappings={}),
            structure=StructureInfo(line_breaks=[], indentation={}, whitespace={})
        ))
        
        # All non-Japanese portions should be present in the result (after stripping)
        result_content = result.reconstructed_content.strip()
        for non_jp_portion in non_japanese_portions:
            assert non_jp_portion in result_content, \
                f"Non-Japanese portion '{non_jp_portion}' not found in result: '{result_content}'"


@given(
    text=mixed_text_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_japanese_only_translation_punctuation_preservation(text: str):
    """
    Property 8: Japanese-only translation (with punctuation)
    Property 9: Punctuation preservation
    
    For any text containing punctuation and symbols,
    their usage and positioning should be preserved after translation.
    
    Validates: Requirements 7.1, 7.4, 7.5
    
    Feature: gitbook-translator, Property 8: Japanese-only translation
    """
    # Add punctuation to the text
    content = f"{text}. This is a test! What about this?"
    
    segments = [
        {
            "type": "translatable",
            "content": content,
            "start_line": 0,
            "end_line": 0,
            "metadata": None
        }
    ]
    
    glossary = {
        "format": "auto-detected",
        "mappings": {}
    }
    
    structure = {
        "line_breaks": [],
        "indentation": {},
        "whitespace": {}
    }
    
    # Mock LLM response that preserves punctuation
    mock_response = Mock()
    # Simulate translation by replacing Japanese with [TRANSLATED]
    translated_content = content
    for jp_portion in extract_japanese_portions(content):
        translated_content = translated_content.replace(jp_portion, "[TRANSLATED]", 1)
    
    mock_response.content = f"[Segment 1]\n{translated_content}"
    
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_response):
        result = tool.translate(TranslationRequest(
            segments=[
                Segment(
                    type=SegmentType.TRANSLATABLE,
                    content=content,
                    start_line=0,
                    end_line=0,
                    metadata=None
                )
            ],
            target_language="en",
            glossary=Glossary(format="auto-detected", mappings={}),
            structure=StructureInfo(line_breaks=[], indentation={}, whitespace={})
        ))
        
        # Punctuation should be preserved
        assert "." in result.reconstructed_content
        assert "!" in result.reconstructed_content
        assert "?" in result.reconstructed_content
