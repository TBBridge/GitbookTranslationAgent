"""Property-based tests for technical term preservation in TranslateContentTool.

Feature: gitbook-translator
Tests for Property 11: Technical term preservation
"""

import os
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

# Japanese text strategy
japanese_text_strategy = st.text(
    alphabet='あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん'
            'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン'
            '漢字文字テスト',
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())

# Technical term strategy - product names, feature names, UI labels, commands
technical_terms = [
    "GitHub", "GitBook", "API", "REST", "JSON", "XML", "HTML", "CSS",
    "JavaScript", "Python", "TypeScript", "React", "Vue", "Angular",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Firebase",
    "MongoDB", "PostgreSQL", "MySQL", "Redis", "Elasticsearch",
    "Linux", "Windows", "macOS", "Ubuntu", "CentOS",
    "npm", "pip", "yarn", "cargo", "maven",
    "git", "svn", "mercurial", "perforce",
    "IDE", "CLI", "GUI", "UI", "UX", "API", "SDK", "HTTP", "HTTPS",
    "OAuth", "JWT", "SSL", "TLS", "SSH", "FTP", "SFTP",
    "CRUD", "REST", "GraphQL", "gRPC", "WebSocket",
    "CI/CD", "DevOps", "Agile", "Scrum", "Kanban",
    "Microservices", "Monolith", "Serverless", "Lambda", "Function",
    "Container", "Image", "Registry", "Repository", "Branch",
    "Commit", "Pull Request", "Merge", "Rebase", "Cherry-pick",
    "Debug", "Profile", "Benchmark", "Test", "Deploy",
    "Production", "Staging", "Development", "QA", "UAT"
]

technical_term_strategy = st.sampled_from(technical_terms)


def has_japanese_characters(text: str) -> bool:
    """Check if text contains Japanese characters."""
    japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]'
    return bool(re.search(japanese_pattern, text))


def extract_technical_terms(text: str, known_terms: list) -> list:
    """Extract technical terms from text that are in the known_terms list."""
    found_terms = []
    for term in known_terms:
        if term in text:
            found_terms.append(term)
    return found_terms


@given(
    japanese_text=japanese_text_strategy,
    technical_term=technical_term_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_technical_term_preservation_not_in_glossary(
    japanese_text: str,
    technical_term: str
):
    """
    Property 11: Technical term preservation
    
    For any text containing product names, feature names, UI labels, commands,
    or technical identifiers NOT in the glossary, those terms should remain
    untranslated after translation.
    
    Validates: Requirements 8.5
    
    Feature: gitbook-translator, Property 11: Technical term preservation
    """
    # Create content with Japanese text and technical term
    content = f"{japanese_text} uses {technical_term} for development"
    
    # Create glossary WITHOUT the technical term
    glossary = Glossary(
        format="auto-detected",
        mappings={}  # Empty glossary - technical term is NOT in glossary
    )
    
    segments = [
        Segment(
            type=SegmentType.TRANSLATABLE,
            content=content,
            start_line=0,
            end_line=0,
            metadata=None
        )
    ]
    
    structure = StructureInfo(
        line_breaks=[],
        indentation={},
        whitespace={}
    )
    
    # Mock LLM response that translates Japanese but preserves technical term
    mock_response = Mock()
    # Simulate translation: replace Japanese with [TRANSLATED] but keep technical term
    translated_content = content.replace(japanese_text, "[TRANSLATED]")
    mock_response.content = f"[Segment 1]\n{translated_content}"
    
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_response):
        result = tool.translate(TranslationRequest(
            segments=segments,
            target_language="en",
            glossary=glossary,
            structure=structure
        ))
        
        # Technical term should be preserved (unchanged) in the output
        assert technical_term in result.reconstructed_content, \
            f"Technical term '{technical_term}' should be preserved in output"


@given(
    japanese_text=japanese_text_strategy,
    technical_term=technical_term_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_technical_term_preservation_in_glossary(
    japanese_text: str,
    technical_term: str
):
    """
    Property 11: Technical term preservation (with glossary)
    
    For any text containing product names, feature names, UI labels, commands,
    or technical identifiers that ARE in the glossary, those terms should be
    translated according to the glossary mapping.
    
    Validates: Requirements 8.3, 8.4, 8.5
    
    Feature: gitbook-translator, Property 11: Technical term preservation
    """
    # Create content with Japanese text and technical term
    content = f"{japanese_text} uses {technical_term} for development"
    
    # Create glossary WITH the technical term mapped to a translation
    glossary_translation = f"[{technical_term}_translated]"
    glossary = Glossary(
        format="auto-detected",
        mappings={
            technical_term: {"en": glossary_translation}
        }
    )
    
    segments = [
        Segment(
            type=SegmentType.TRANSLATABLE,
            content=content,
            start_line=0,
            end_line=0,
            metadata=None
        )
    ]
    
    structure = StructureInfo(
        line_breaks=[],
        indentation={},
        whitespace={}
    )
    
    # Mock LLM response that applies glossary translation
    mock_response = Mock()
    # Simulate translation: replace Japanese with [TRANSLATED] and apply glossary
    translated_content = content.replace(japanese_text, "[TRANSLATED]")
    translated_content = translated_content.replace(technical_term, glossary_translation)
    mock_response.content = f"[Segment 1]\n{translated_content}"
    
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_response):
        result = tool.translate(TranslationRequest(
            segments=segments,
            target_language="en",
            glossary=glossary,
            structure=structure
        ))
        
        # Glossary translation should be applied
        assert glossary_translation in result.reconstructed_content, \
            f"Glossary translation '{glossary_translation}' should be in output"


@given(
    japanese_text=japanese_text_strategy,
    term1=technical_term_strategy,
    term2=technical_term_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_technical_term_preservation_multiple_terms(
    japanese_text: str,
    term1: str,
    term2: str
):
    """
    Property 11: Technical term preservation (multiple terms)
    
    For any text containing multiple technical terms not in the glossary,
    all of them should remain untranslated.
    
    Validates: Requirements 8.5
    
    Feature: gitbook-translator, Property 11: Technical term preservation
    """
    # Skip if terms are the same
    assume(term1 != term2)
    
    # Create content with Japanese text and multiple technical terms
    content = f"{japanese_text} uses {term1} and {term2} for development"
    
    # Create empty glossary - no terms are in glossary
    glossary = Glossary(
        format="auto-detected",
        mappings={}
    )
    
    segments = [
        Segment(
            type=SegmentType.TRANSLATABLE,
            content=content,
            start_line=0,
            end_line=0,
            metadata=None
        )
    ]
    
    structure = StructureInfo(
        line_breaks=[],
        indentation={},
        whitespace={}
    )
    
    # Mock LLM response that preserves both technical terms
    mock_response = Mock()
    translated_content = content.replace(japanese_text, "[TRANSLATED]")
    mock_response.content = f"[Segment 1]\n{translated_content}"
    
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_response):
        result = tool.translate(TranslationRequest(
            segments=segments,
            target_language="en",
            glossary=glossary,
            structure=structure
        ))
        
        # Both technical terms should be preserved
        assert term1 in result.reconstructed_content, \
            f"Technical term '{term1}' should be preserved in output"
        assert term2 in result.reconstructed_content, \
            f"Technical term '{term2}' should be preserved in output"


@given(
    japanese_text=japanese_text_strategy,
    technical_term=technical_term_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_technical_term_preservation_case_sensitive(
    japanese_text: str,
    technical_term: str
):
    """
    Property 11: Technical term preservation (case sensitivity)
    
    For any text containing technical terms, the case should be preserved
    exactly as it appears in the original (case-sensitive preservation).
    
    Validates: Requirements 8.5
    
    Feature: gitbook-translator, Property 11: Technical term preservation
    """
    # Create content with Japanese text and technical term
    content = f"{japanese_text} uses {technical_term} for development"
    
    # Create empty glossary
    glossary = Glossary(
        format="auto-detected",
        mappings={}
    )
    
    segments = [
        Segment(
            type=SegmentType.TRANSLATABLE,
            content=content,
            start_line=0,
            end_line=0,
            metadata=None
        )
    ]
    
    structure = StructureInfo(
        line_breaks=[],
        indentation={},
        whitespace={}
    )
    
    # Mock LLM response that preserves technical term with exact case
    mock_response = Mock()
    translated_content = content.replace(japanese_text, "[TRANSLATED]")
    mock_response.content = f"[Segment 1]\n{translated_content}"
    
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_response):
        result = tool.translate(TranslationRequest(
            segments=segments,
            target_language="en",
            glossary=glossary,
            structure=structure
        ))
        
        # Technical term should be preserved with exact case
        assert technical_term in result.reconstructed_content, \
            f"Technical term '{technical_term}' should be preserved with exact case"
        
        # Verify case is preserved (not lowercased or uppercased)
        # Count occurrences of the term
        count_original = content.count(technical_term)
        count_result = result.reconstructed_content.count(technical_term)
        assert count_original == count_result, \
            f"Technical term case should be preserved: expected {count_original} occurrences, got {count_result}"


@given(
    japanese_text=japanese_text_strategy,
    technical_term=technical_term_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_technical_term_preservation_in_context(
    japanese_text: str,
    technical_term: str
):
    """
    Property 11: Technical term preservation (in context)
    
    For any text containing technical terms in various contexts
    (beginning, middle, end of sentence), all occurrences should
    remain untranslated.
    
    Validates: Requirements 8.5
    
    Feature: gitbook-translator, Property 11: Technical term preservation
    """
    # Create content with technical term in multiple positions
    content = f"{technical_term} is used with {japanese_text}. The {technical_term} tool helps. Use {technical_term}."
    
    # Create empty glossary
    glossary = Glossary(
        format="auto-detected",
        mappings={}
    )
    
    segments = [
        Segment(
            type=SegmentType.TRANSLATABLE,
            content=content,
            start_line=0,
            end_line=0,
            metadata=None
        )
    ]
    
    structure = StructureInfo(
        line_breaks=[],
        indentation={},
        whitespace={}
    )
    
    # Mock LLM response that preserves technical term in all positions
    mock_response = Mock()
    translated_content = content.replace(japanese_text, "[TRANSLATED]")
    mock_response.content = f"[Segment 1]\n{translated_content}"
    
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(tool.llm.__class__, 'invoke', return_value=mock_response):
        result = tool.translate(TranslationRequest(
            segments=segments,
            target_language="en",
            glossary=glossary,
            structure=structure
        ))
        
        # Count occurrences of technical term in original and result
        original_count = content.count(technical_term)
        result_count = result.reconstructed_content.count(technical_term)
        
        # All occurrences should be preserved
        assert original_count == result_count, \
            f"All occurrences of '{technical_term}' should be preserved: " \
            f"expected {original_count}, got {result_count}"
