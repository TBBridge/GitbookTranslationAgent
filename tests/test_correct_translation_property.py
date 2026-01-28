"""Property-based tests for CorrectTranslationTool.

Feature: gitbook-translator
Tests for Properties 1, 6, 7, 9, 12 related to correction and preservation.
"""

import json
import re
from unittest.mock import Mock, patch
from hypothesis import given, settings, strategies as st, assume, HealthCheck
from langchain_core.messages import AIMessage

from src.tools.correct_translation import CorrectTranslationTool
from src.tools.parse_markdown import ParseMarkdownTool


# Strategies for generating markdown content
simple_text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() and '[' not in x and ']' not in x and '(' not in x and ')' not in x)

code_content_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P')),
    min_size=1,
    max_size=50
).filter(lambda x: '`' not in x and '\n' not in x)

url_strategy = st.from_regex(r'https?://[a-zA-Z0-9\-\.]+\.[a-z]{2,}(/[a-zA-Z0-9\-_\.]*)*', fullmatch=True)

path_strategy = st.from_regex(r'[a-zA-Z0-9\-_]+(/[a-zA-Z0-9\-_]+)*\.[a-z]{2,4}', fullmatch=True)


def count_line_breaks(text: str) -> int:
    """Count the number of line breaks in text."""
    return text.count('\n')


def count_leading_spaces(line: str) -> int:
    """Count leading spaces in a line."""
    return len(line) - len(line.lstrip(' '))


def extract_table_structure(text: str) -> list:
    """Extract table rows from markdown."""
    lines = text.split('\n')
    table_lines = []
    for line in lines:
        if '|' in line:
            table_lines.append(line)
    return table_lines


def count_table_columns(table_line: str) -> int:
    """Count columns in a markdown table line."""
    # Split by pipe and count non-empty cells
    cells = table_line.split('|')
    # Remove first and last empty cells from split
    return len([c for c in cells[1:-1] if c.strip()])


def is_valid_markdown(text: str) -> bool:
    """Check if text is valid markdown (basic check)."""
    # Check for balanced brackets
    if text.count('[') != text.count(']'):
        return False
    if text.count('(') != text.count(')'):
        return False
    if text.count('`') % 2 != 0:
        return False
    if text.count('*') % 2 != 0 and '**' not in text:
        return False
    return True


@given(
    lines=st.lists(
        st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P')), min_size=0, max_size=50),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_property_whitespace_preservation(lines: list):
    """
    Property 1: Whitespace preservation
    
    For any markdown file, after correction, all line breaks, blank lines,
    indentation, and spacing should be identical to the original.
    
    Validates: Requirements 3.1
    
    Feature: gitbook-translator, Property 1: Whitespace preservation
    """
    # Create markdown with various whitespace patterns
    original_content = '\n'.join(lines)
    
    # Count original whitespace
    original_line_breaks = count_line_breaks(original_content)
    original_indentation = {}
    for i, line in enumerate(original_content.split('\n')):
        if line and line[0] == ' ':
            original_indentation[i] = count_leading_spaces(line)
    
    # Create correction tool with mocked LLM
    with patch('src.tools.correct_translation.ChatOpenAI') as mock_llm_class:
        tool = CorrectTranslationTool()
        
        # Mock LLM to return content with preserved whitespace
        mock_response = AIMessage(content=original_content)
        tool.llm.invoke = Mock(return_value=mock_response)
        
        issues = [
            {
                "severity": "MINOR",
                "category": "style",
                "line": 1,
                "description": "Minor style improvement",
                "suggestion": "Improve phrasing"
            }
        ]
        
        result_json = tool._run(
            content=original_content,
            issues=issues,
            target_language="en"
        )
        
        result = json.loads(result_json)
        corrected_content = result["corrected_content"]
        
        # Verify line breaks are preserved
        corrected_line_breaks = count_line_breaks(corrected_content)
        assert corrected_line_breaks == original_line_breaks, \
            f"Line breaks changed: {original_line_breaks} -> {corrected_line_breaks}"
        
        # Verify indentation is preserved
        corrected_lines = corrected_content.split('\n')
        for i, line in enumerate(corrected_lines):
            if i in original_indentation:
                corrected_indent = count_leading_spaces(line)
                assert corrected_indent == original_indentation[i], \
                    f"Indentation changed on line {i}: {original_indentation[i]} -> {corrected_indent}"


@given(
    num_columns=st.integers(min_value=2, max_value=5),
    num_rows=st.integers(min_value=2, max_value=5)
)
@settings(max_examples=50, deadline=None)
def test_property_table_structure_preservation(num_columns: int, num_rows: int):
    """
    Property 6: Table structure preservation
    
    For any markdown file containing tables, after correction, the number of columns,
    pipe characters, and alignment markers should be identical to the original.
    
    Validates: Requirements 6.1, 6.3, 6.4
    
    Feature: gitbook-translator, Property 6: Table structure preservation
    """
    # Create a markdown table
    header = '| ' + ' | '.join([f'Col{i}' for i in range(num_columns)]) + ' |'
    separator = '| ' + ' | '.join(['---' for _ in range(num_columns)]) + ' |'
    rows = []
    for r in range(num_rows):
        row = '| ' + ' | '.join([f'Cell{r}{c}' for c in range(num_columns)]) + ' |'
        rows.append(row)
    
    original_content = header + '\n' + separator + '\n' + '\n'.join(rows)
    
    # Count original table structure
    original_table_lines = extract_table_structure(original_content)
    original_column_counts = [count_table_columns(line) for line in original_table_lines]
    original_pipe_counts = [line.count('|') for line in original_table_lines]
    
    # Create correction tool with mocked LLM
    with patch('src.tools.correct_translation.ChatOpenAI'):
        tool = CorrectTranslationTool()
        
        # Mock LLM to return content with preserved table structure
        mock_response = AIMessage(content=original_content)
        tool.llm.invoke = Mock(return_value=mock_response)
        
        issues = [
            {
                "severity": "MINOR",
                "category": "style",
                "line": 1,
                "description": "Minor improvement",
                "suggestion": "Improve text"
            }
        ]
        
        result_json = tool._run(
            content=original_content,
            issues=issues,
            target_language="en"
        )
        
        result = json.loads(result_json)
        corrected_content = result["corrected_content"]
        
        # Verify table structure is preserved
        corrected_table_lines = extract_table_structure(corrected_content)
        corrected_column_counts = [count_table_columns(line) for line in corrected_table_lines]
        corrected_pipe_counts = [line.count('|') for line in corrected_table_lines]
        
        assert corrected_column_counts == original_column_counts, \
            f"Column counts changed: {original_column_counts} -> {corrected_column_counts}"
        
        assert corrected_pipe_counts == original_pipe_counts, \
            f"Pipe counts changed: {original_pipe_counts} -> {corrected_pipe_counts}"


@given(
    num_columns=st.integers(min_value=2, max_value=4),
    num_rows=st.integers(min_value=1, max_value=3)
)
@settings(max_examples=100, deadline=None)
def test_property_table_cell_translation(num_columns: int, num_rows: int):
    """
    Property 7: Table cell translation
    
    For any markdown table with Japanese content in cells, after correction,
    only cell content should be translated while maintaining the exact column structure.
    
    Validates: Requirements 6.2
    
    Feature: gitbook-translator, Property 7: Table cell translation
    """
    # Create a markdown table with Japanese content
    header = '| ' + ' | '.join([f'Col{i}' for i in range(num_columns)]) + ' |'
    separator = '| ' + ' | '.join(['---' for _ in range(num_columns)]) + ' |'
    rows = []
    for r in range(num_rows):
        row = '| ' + ' | '.join([f'セル{r}{c}' for c in range(num_columns)]) + ' |'
        rows.append(row)
    
    original_content = header + '\n' + separator + '\n' + '\n'.join(rows)
    
    # Count original structure
    original_table_lines = extract_table_structure(original_content)
    original_column_counts = [count_table_columns(line) for line in original_table_lines]
    
    # Create correction tool
    with patch('src.tools.correct_translation.ChatOpenAI'):
        tool = CorrectTranslationTool()
        
        # Mock LLM to return content with translated cells but preserved structure
        corrected_content = original_content.replace('セル', 'Cell')
        mock_response = AIMessage(content=corrected_content)
        tool.llm.invoke = Mock(return_value=mock_response)
        
        issues = [
            {
                "severity": "MAJOR",
                "category": "completeness",
                "line": 3,
                "description": "Japanese text not translated",
                "suggestion": "Translate Japanese to English"
            }
        ]
        
        result_json = tool._run(
            content=original_content,
            issues=issues,
            target_language="en"
        )
        
        result = json.loads(result_json)
        result_content = result["corrected_content"]
        
        # Verify table structure is preserved
        result_table_lines = extract_table_structure(result_content)
        result_column_counts = [count_table_columns(line) for line in result_table_lines]
        
        assert result_column_counts == original_column_counts, \
            f"Column structure changed: {original_column_counts} -> {result_column_counts}"
        
        # Verify content was translated
        assert 'Cell' in result_content or 'セル' not in result_content or result_content != original_content


@given(
    text=st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?;:-',
        min_size=1,
        max_size=100
    ).filter(lambda x: x.strip())
)
@settings(max_examples=100, deadline=None)
def test_property_punctuation_preservation(text: str):
    """
    Property 9: Punctuation preservation
    
    For any text containing punctuation and symbols, their usage and positioning
    should be preserved after correction.
    
    Validates: Requirements 7.5
    
    Feature: gitbook-translator, Property 9: Punctuation preservation
    """
    # Create content with punctuation
    original_content = f"{text}. This is a test! What about this? Yes, indeed."
    
    # Count original punctuation
    original_periods = original_content.count('.')
    original_exclamations = original_content.count('!')
    original_questions = original_content.count('?')
    original_commas = original_content.count(',')
    
    # Create correction tool
    with patch('src.tools.correct_translation.ChatOpenAI'):
        tool = CorrectTranslationTool()
        
        # Mock LLM to return content with preserved punctuation
        mock_response = AIMessage(content=original_content)
        tool.llm.invoke = Mock(return_value=mock_response)
        
        issues = [
            {
                "severity": "MINOR",
                "category": "style",
                "line": 1,
                "description": "Improve phrasing",
                "suggestion": "Use more formal language"
            }
        ]
        
        result_json = tool._run(
            content=original_content,
            issues=issues,
            target_language="en"
        )
        
        result = json.loads(result_json)
        corrected_content = result["corrected_content"]
        
        # Verify punctuation is preserved
        corrected_periods = corrected_content.count('.')
        corrected_exclamations = corrected_content.count('!')
        corrected_questions = corrected_content.count('?')
        corrected_commas = corrected_content.count(',')
        
        assert corrected_periods == original_periods, \
            f"Period count changed: {original_periods} -> {corrected_periods}"
        
        assert corrected_exclamations == original_exclamations, \
            f"Exclamation count changed: {original_exclamations} -> {corrected_exclamations}"
        
        assert corrected_questions == original_questions, \
            f"Question mark count changed: {original_questions} -> {corrected_questions}"
        
        assert corrected_commas == original_commas, \
            f"Comma count changed: {original_commas} -> {corrected_commas}"


@given(
    text=st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n*_`[](){}',
        min_size=1,
        max_size=100
    ).filter(lambda x: x.strip())
)
@settings(max_examples=100, deadline=None)
def test_property_markdown_validity_preservation(text: str):
    """
    Property 12: Markdown validity preservation
    
    For any valid markdown file, after correction, the output should be valid
    markdown that can be parsed without errors.
    
    Validates: Requirements 9.5
    
    Feature: gitbook-translator, Property 12: Markdown validity preservation
    """
    # Create valid markdown content
    original_content = f"# Title\n\n{text}\n\n**bold** and *italic*"
    
    # Verify original is valid markdown
    assume(is_valid_markdown(original_content))
    
    # Create correction tool
    with patch('src.tools.correct_translation.ChatOpenAI'):
        tool = CorrectTranslationTool()
        
        # Mock LLM to return valid markdown
        mock_response = AIMessage(content=original_content)
        tool.llm.invoke = Mock(return_value=mock_response)
        
        issues = [
            {
                "severity": "MINOR",
                "category": "style",
                "line": 3,
                "description": "Improve phrasing",
                "suggestion": "Use more formal language"
            }
        ]
        
        result_json = tool._run(
            content=original_content,
            issues=issues,
            target_language="en"
        )
        
        result = json.loads(result_json)
        corrected_content = result["corrected_content"]
        
        # Verify corrected content is valid markdown
        assert is_valid_markdown(corrected_content), \
            f"Corrected content is not valid markdown: {corrected_content}"


@given(
    code_content=code_content_strategy,
    text_before=simple_text_strategy,
    text_after=simple_text_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_code_block_preservation_in_correction(code_content: str, text_before: str, text_after: str):
    """
    Property 2: Protected region round-trip (for correction)
    
    For any markdown containing code blocks, those blocks should be
    byte-identical after correction.
    
    Validates: Requirements 3.2, 4.1
    
    Feature: gitbook-translator, Property 2: Protected region round-trip
    """
    # Create markdown with code block
    original_content = f"{text_before}\n```python\n{code_content}\n```\n{text_after}"
    
    # Create correction tool
    with patch('src.tools.correct_translation.ChatOpenAI'):
        tool = CorrectTranslationTool()
        
        # Mock LLM to return content with preserved code block
        mock_response = AIMessage(content=original_content)
        tool.llm.invoke = Mock(return_value=mock_response)
        
        issues = [
            {
                "severity": "MINOR",
                "category": "style",
                "line": 1,
                "description": "Improve text",
                "suggestion": "Better phrasing"
            }
        ]
        
        result_json = tool._run(
            content=original_content,
            issues=issues,
            target_language="en"
        )
        
        result = json.loads(result_json)
        corrected_content = result["corrected_content"]
        
        # Verify code block is preserved
        assert f"```python\n{code_content}\n```" in corrected_content, \
            "Code block was not preserved during correction"


@given(
    link_text=simple_text_strategy,
    url=url_strategy
)
@settings(max_examples=100, deadline=None)
def test_property_link_preservation_in_correction(link_text: str, url: str):
    """
    Property 3: Link URL preservation (for correction)
    
    For any markdown containing links, URLs should remain unchanged after correction.
    
    Validates: Requirements 5.1
    
    Feature: gitbook-translator, Property 3: Link URL preservation
    """
    # Create markdown with link
    original_content = f"Check out [{link_text}]({url}) for more info"
    
    # Create correction tool
    with patch('src.tools.correct_translation.ChatOpenAI'):
        tool = CorrectTranslationTool()
        
        # Mock LLM to return content with preserved URL
        mock_response = AIMessage(content=original_content)
        tool.llm.invoke = Mock(return_value=mock_response)
        
        issues = [
            {
                "severity": "MINOR",
                "category": "style",
                "line": 1,
                "description": "Improve text",
                "suggestion": "Better phrasing"
            }
        ]
        
        result_json = tool._run(
            content=original_content,
            issues=issues,
            target_language="en"
        )
        
        result = json.loads(result_json)
        corrected_content = result["corrected_content"]
        
        # Verify URL is preserved
        assert url in corrected_content, \
            f"URL was not preserved: {url} not in {corrected_content}"
