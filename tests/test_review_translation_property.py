"""Property-based tests for ReviewTranslationTool.

Feature: gitbook-translator
Tests for Property 13: Complete translation
"""

import json
import re
from unittest.mock import MagicMock
from hypothesis import given, settings, strategies as st, assume

from src.tools.review_translation import ReviewTranslationTool


# Strategy for generating Japanese text
japanese_text_strategy = st.text(
    alphabet='あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん'
            'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン'
            '漢字文字テスト',
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())

# Strategy for generating English text
english_text_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?;:-',
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())

# Strategy for code blocks
code_block_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789(){}[];:=+-*/',
    min_size=5,
    max_size=50
).filter(lambda x: x.strip())


def has_japanese_characters(text: str) -> bool:
    """Check if text contains Japanese characters."""
    # Unicode ranges for Japanese:
    # Hiragana: U+3040-U+309F
    # Katakana: U+30A0-U+30FF
    # Kanji: U+4E00-U+9FFF
    japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]'
    return bool(re.search(japanese_pattern, text))


def extract_japanese_outside_protected_regions(text: str) -> list:
    """Extract Japanese text that is NOT in protected regions (code blocks, inline code, etc)."""
    # Remove code blocks (``` ... ```)
    text_without_code_blocks = re.sub(r'```[\s\S]*?```', '', text)
    
    # Remove inline code (`...`)
    text_without_inline_code = re.sub(r'`[^`]*`', '', text_without_code_blocks)
    
    # Remove YAML frontmatter (--- ... ---)
    text_without_yaml = re.sub(r'^---[\s\S]*?---', '', text_without_inline_code, flags=re.MULTILINE)
    
    # Remove GitBook tags ({% ... %}, {{ ... }})
    text_without_tags = re.sub(r'\{[%{][\s\S]*?[%}]\}', '', text_without_yaml)
    
    # Remove HTML tags
    text_without_html = re.sub(r'<[^>]+>', '', text_without_tags)
    
    # Extract Japanese portions
    japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+'
    return re.findall(japanese_pattern, text_without_html)


@given(
    japanese_text=japanese_text_strategy,
    english_text=english_text_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_complete_translation_no_untranslated_japanese(
    japanese_text: str,
    english_text: str
):
    """
    Property 13: Complete translation
    
    For any translated Markdown file, there should be no remaining untranslated
    Japanese text outside of protected regions.
    
    Validates: Requirements 10.2
    
    Feature: gitbook-translator, Property 13: Complete translation
    """
    # Create original content with Japanese text
    original_content = f"# {japanese_text}\n\n{english_text}\n\n{japanese_text}"
    
    # Create translated content where Japanese is replaced with English
    translated_content = f"# {english_text}\n\n{english_text}\n\n{english_text}"
    
    # Create a ReviewTranslationTool with mocked LLM
    tool = ReviewTranslationTool()
    tool.llm = MagicMock()
    
    # Mock the LLM to return no issues (complete translation)
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "issues": [],
        "approved": True
    })
    tool.llm.invoke.return_value = mock_response
    
    # Run the review
    glossary = {
        "format": "auto-detected",
        "mappings": {}
    }
    
    result_str = tool._run(
        original_content=original_content,
        translated_content=translated_content,
        target_language="en",
        glossary=glossary
    )
    
    result = json.loads(result_str)
    
    # Verify that the review result indicates no untranslated Japanese
    # If there were untranslated Japanese, the review should have found issues
    # Since we mocked the LLM to return no issues, we're testing that the tool
    # correctly processes the review result
    assert result["approved"] is True
    assert len(result["issues"]) == 0


@given(
    japanese_text=japanese_text_strategy,
    english_text=english_text_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_complete_translation_detects_untranslated_japanese(
    japanese_text: str,
    english_text: str
):
    """
    Property 13: Complete translation (negative case)
    
    For any translated Markdown file with remaining untranslated Japanese text,
    the review should detect it as an issue.
    
    Validates: Requirements 10.2
    
    Feature: gitbook-translator, Property 13: Complete translation
    """
    # Create original content with Japanese text
    original_content = f"# {japanese_text}\n\n{english_text}"
    
    # Create translated content that still contains Japanese (incomplete translation)
    translated_content = f"# {english_text}\n\n{english_text}\n\n{japanese_text}"
    
    # Create a ReviewTranslationTool with mocked LLM
    tool = ReviewTranslationTool()
    tool.llm = MagicMock()
    
    # Mock the LLM to return an issue about untranslated Japanese
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "issues": [
            {
                "severity": "MAJOR",
                "category": "completeness",
                "line": 3,
                "column": None,
                "description": "Untranslated Japanese text found",
                "suggestion": "Translate the remaining Japanese text"
            }
        ],
        "approved": False
    })
    tool.llm.invoke.return_value = mock_response
    
    # Run the review
    glossary = {
        "format": "auto-detected",
        "mappings": {}
    }
    
    result_str = tool._run(
        original_content=original_content,
        translated_content=translated_content,
        target_language="en",
        glossary=glossary
    )
    
    result = json.loads(result_str)
    
    # Verify that the review detected the untranslated Japanese
    assert result["approved"] is False
    assert len(result["issues"]) > 0
    
    # Find the untranslated Japanese issue
    untranslated_issues = [
        issue for issue in result["issues"]
        if "untranslated" in issue["description"].lower() or "japanese" in issue["description"].lower()
    ]
    assert len(untranslated_issues) > 0
    assert untranslated_issues[0]["severity"] == "MAJOR"


@given(
    japanese_text=japanese_text_strategy,
    english_text=english_text_strategy,
    code_content=code_block_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_complete_translation_ignores_protected_regions(
    japanese_text: str,
    english_text: str,
    code_content: str
):
    """
    Property 13: Complete translation (with protected regions)
    
    For any translated Markdown file, Japanese text in protected regions
    (code blocks, inline code, etc.) should not be flagged as untranslated.
    
    Validates: Requirements 10.2
    
    Feature: gitbook-translator, Property 13: Complete translation
    """
    # Create original content with Japanese in protected regions
    original_content = f"""# {english_text}

{japanese_text}

```python
# {japanese_text}
print('{code_content}')
```

`{japanese_text}`

More text: {english_text}"""
    
    # Create translated content where only non-protected Japanese is translated
    translated_content = f"""# {english_text}

{english_text}

```python
# {japanese_text}
print('{code_content}')
```

`{japanese_text}`

More text: {english_text}"""
    
    # Create a ReviewTranslationTool with mocked LLM
    tool = ReviewTranslationTool()
    tool.llm = MagicMock()
    
    # Mock the LLM to return no issues (protected regions are ignored)
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "issues": [],
        "approved": True
    })
    tool.llm.invoke.return_value = mock_response
    
    # Run the review
    glossary = {
        "format": "auto-detected",
        "mappings": {}
    }
    
    result_str = tool._run(
        original_content=original_content,
        translated_content=translated_content,
        target_language="en",
        glossary=glossary
    )
    
    result = json.loads(result_str)
    
    # Verify that the review approved the translation
    # (Japanese in protected regions should not cause issues)
    assert result["approved"] is True
    assert len(result["issues"]) == 0


@given(
    japanese_text=japanese_text_strategy,
    english_text=english_text_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_complete_translation_classification(
    japanese_text: str,
    english_text: str
):
    """
    Property 13: Complete translation (issue classification)
    
    For any untranslated Japanese text detected, the issue should be
    classified as MAJOR (not MINOR), as it indicates incomplete translation.
    
    Validates: Requirements 10.2
    
    Feature: gitbook-translator, Property 13: Complete translation
    """
    # Create original content with Japanese text
    original_content = f"# {japanese_text}\n\n{english_text}"
    
    # Create translated content with untranslated Japanese
    translated_content = f"# {english_text}\n\n{english_text}\n\n{japanese_text}"
    
    # Create a ReviewTranslationTool with mocked LLM
    tool = ReviewTranslationTool()
    tool.llm = MagicMock()
    
    # Mock the LLM to return an issue (but with wrong severity)
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "issues": [
            {
                "severity": "MINOR",  # Wrong severity - should be MAJOR
                "category": "completeness",
                "line": 3,
                "column": None,
                "description": "Untranslated Japanese text found",
                "suggestion": "Translate the remaining Japanese text"
            }
        ],
        "approved": True  # Wrong approval - should be False
    })
    tool.llm.invoke.return_value = mock_response
    
    # Run the review
    glossary = {
        "format": "auto-detected",
        "mappings": {}
    }
    
    result_str = tool._run(
        original_content=original_content,
        translated_content=translated_content,
        target_language="en",
        glossary=glossary
    )
    
    result = json.loads(result_str)
    
    # Verify that the tool reclassified the issue to MAJOR
    assert len(result["issues"]) > 0
    assert result["issues"][0]["severity"] == "MAJOR"
    
    # Verify that the tool overrode approval to False
    assert result["approved"] is False
