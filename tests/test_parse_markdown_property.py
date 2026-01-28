"""Property-based tests for ParseMarkdownTool.

Feature: gitbook-translator
Tests for Properties 2, 3, 4, 5 related to markdown parsing and protection.
"""

import json
from hypothesis import given, settings, strategies as st, assume

from src.tools.parse_markdown import ParseMarkdownTool
from src.models.markdown_models import SegmentType


# Strategies for generating markdown content
simple_text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')),
    min_size=1,
    max_size=50
).filter(lambda x: '[' not in x and ']' not in x and '(' not in x and ')' not in x and '`' not in x)

code_content_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P')),
    min_size=1,
    max_size=50
).filter(lambda x: '`' not in x and '\n' not in x)

url_strategy = st.from_regex(r'https?://[a-zA-Z0-9\-\.]+\.[a-z]{2,}(/[a-zA-Z0-9\-_\.]*)*', fullmatch=True)

path_strategy = st.from_regex(r'[a-zA-Z0-9\-_]+(/[a-zA-Z0-9\-_]+)*\.[a-z]{2,4}', fullmatch=True)


def reconstruct_content_from_segments(segments: list) -> str:
    """Reconstruct content from parsed segments."""
    return ''.join(seg['content'] for seg in segments)


@given(code_content=code_content_strategy)
@settings(max_examples=100)
def test_property_fenced_code_block_round_trip(code_content: str):
    """
    Property 2: Protected region round-trip
    
    For any markdown containing fenced code blocks, those blocks should be
    byte-identical after parsing.
    Validates: Requirements 3.2, 4.1
    """
    # Create markdown with fenced code block
    markdown = f"Some text\n```python\n{code_content}\n```\nMore text"
    
    tool = ParseMarkdownTool()
    result_json = tool._run(markdown)
    result = json.loads(result_json)
    
    assert result["success"] is True
    
    # Reconstruct content from segments
    reconstructed = reconstruct_content_from_segments(result["segments"])
    
    # Content should be identical
    assert reconstructed == markdown
    
    # Find the code block segment
    code_block_found = False
    for seg in result["segments"]:
        if seg["metadata"] and seg["metadata"]["protection_reason"] == "code-block":
            code_block_found = True
            # Code block should be protected
            assert seg["type"] == "protected"
            # Code block content should be preserved exactly
            assert code_content in seg["content"]
    
    assert code_block_found, "Code block should be detected as protected"


@given(code_content=code_content_strategy)
@settings(max_examples=100)
def test_property_inline_code_round_trip(code_content: str):
    """
    Property 2: Protected region round-trip
    
    For any markdown containing inline code, that code should be
    byte-identical after parsing.
    Validates: Requirements 4.2
    """
    # Create markdown with inline code
    markdown = f"Some text with `{code_content}` inline code"
    
    tool = ParseMarkdownTool()
    result_json = tool._run(markdown)
    result = json.loads(result_json)
    
    assert result["success"] is True
    
    # Reconstruct content from segments
    reconstructed = reconstruct_content_from_segments(result["segments"])
    
    # Content should be identical
    assert reconstructed == markdown


@given(
    key=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=20),
    value=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=50)
)
@settings(max_examples=100)
def test_property_yaml_frontmatter_round_trip(key: str, value: str):
    """
    Property 2: Protected region round-trip
    
    For any markdown containing YAML frontmatter, that frontmatter should be
    byte-identical after parsing.
    Validates: Requirements 3.2, 4.5
    """
    # Create markdown with YAML frontmatter
    markdown = f"---\n{key}: {value}\n---\nContent here"
    
    tool = ParseMarkdownTool()
    result_json = tool._run(markdown)
    result = json.loads(result_json)
    
    assert result["success"] is True
    
    # Reconstruct content from segments
    reconstructed = reconstruct_content_from_segments(result["segments"])
    
    # Content should be identical
    assert reconstructed == markdown
    
    # Find the YAML frontmatter segment
    yaml_found = False
    for seg in result["segments"]:
        if seg["metadata"] and seg["metadata"]["protection_reason"] == "yaml-frontmatter":
            yaml_found = True
            assert seg["type"] == "protected"
            assert key in seg["content"]
            assert value in seg["content"]
    
    assert yaml_found, "YAML frontmatter should be detected as protected"


@given(tag_content=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=20))
@settings(max_examples=100)
def test_property_gitbook_tags_round_trip(tag_content: str):
    """
    Property 2: Protected region round-trip
    
    For any markdown containing GitBook tags, those tags should be
    byte-identical after parsing.
    Validates: Requirements 3.3, 3.4
    """
    # Create markdown with GitBook tags
    markdown1 = f"Text before {{% {tag_content} %}} text after"
    markdown2 = f"Text before {{{{ {tag_content} }}}} text after"
    
    tool = ParseMarkdownTool()
    
    # Test {% ... %} tags
    result_json1 = tool._run(markdown1)
    result1 = json.loads(result_json1)
    assert result1["success"] is True
    reconstructed1 = reconstruct_content_from_segments(result1["segments"])
    assert reconstructed1 == markdown1
    
    # Test {{ ... }} expressions
    result_json2 = tool._run(markdown2)
    result2 = json.loads(result_json2)
    assert result2["success"] is True
    reconstructed2 = reconstruct_content_from_segments(result2["segments"])
    assert reconstructed2 == markdown2


@given(
    tag_name=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=10),
    attr_name=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=10),
    attr_value=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=20)
)
@settings(max_examples=100)
def test_property_html_tags_round_trip(tag_name: str, attr_name: str, attr_value: str):
    """
    Property 2: Protected region round-trip
    
    For any markdown containing HTML tags, those tags should be
    byte-identical after parsing.
    Validates: Requirements 3.5
    """
    # Create markdown with HTML tags
    markdown = f"Text before <{tag_name} {attr_name}=\"{attr_value}\">content</{tag_name}> text after"
    
    tool = ParseMarkdownTool()
    result_json = tool._run(markdown)
    result = json.loads(result_json)
    
    assert result["success"] is True
    
    # Reconstruct content from segments
    reconstructed = reconstruct_content_from_segments(result["segments"])
    
    # Content should be identical
    assert reconstructed == markdown


@given(
    link_text=simple_text_strategy,
    url=url_strategy
)
@settings(max_examples=100)
def test_property_link_url_preservation(link_text: str, url: str):
    """
    Property 3: Link URL preservation
    
    For any markdown containing links [text](URL), all URLs should remain
    unchanged after parsing while display text can be translated.
    Validates: Requirements 5.1
    """
    # Create markdown with link
    markdown = f"Check out [{link_text}]({url}) for more info"
    
    tool = ParseMarkdownTool()
    result_json = tool._run(markdown)
    result = json.loads(result_json)
    
    assert result["success"] is True
    
    # Find the URL segment
    url_found = False
    for seg in result["segments"]:
        if seg["metadata"] and seg["metadata"]["protection_reason"] == "link-url":
            url_found = True
            # URL should be protected
            assert seg["type"] == "protected"
            # URL should be preserved exactly
            assert seg["content"] == url
            assert seg["metadata"]["link_url"] == url
    
    assert url_found, "Link URL should be detected as protected"
    
    # Reconstruct content
    reconstructed = reconstruct_content_from_segments(result["segments"])
    assert reconstructed == markdown


@given(
    alt_text=simple_text_strategy,
    image_path=path_strategy
)
@settings(max_examples=100)
def test_property_image_path_preservation(alt_text: str, image_path: str):
    """
    Property 4: Image path preservation
    
    For any markdown containing images ![alt](path), all paths should remain
    unchanged after parsing while alt text can be translated.
    Validates: Requirements 5.2
    """
    # Create markdown with image
    markdown = f"Here is an image: ![{alt_text}]({image_path})"
    
    tool = ParseMarkdownTool()
    result_json = tool._run(markdown)
    result = json.loads(result_json)
    
    assert result["success"] is True
    
    # Find the image path segment
    path_found = False
    for seg in result["segments"]:
        if seg["metadata"] and seg["metadata"]["protection_reason"] == "image-path":
            path_found = True
            # Path should be protected
            assert seg["type"] == "protected"
            # Path should be preserved exactly
            assert seg["content"] == image_path
            assert seg["metadata"]["link_url"] == image_path
            assert seg["metadata"]["alt_text"] == alt_text
    
    assert path_found, "Image path should be detected as protected"
    
    # Reconstruct content
    reconstructed = reconstruct_content_from_segments(result["segments"])
    assert reconstructed == markdown


@given(
    relative_path=path_strategy
)
@settings(max_examples=100)
def test_property_relative_path_preservation(relative_path: str):
    """
    Property 5: Relative path preservation
    
    For any markdown containing relative paths, anchor links, or file references,
    all such references should remain unchanged after parsing.
    Validates: Requirements 5.3, 5.4, 5.5
    """
    # Test relative path in link
    markdown1 = f"See [{relative_path}]({relative_path})"
    
    # Test anchor link
    anchor = f"#{relative_path}"
    markdown2 = f"Jump to [section]({anchor})"
    
    tool = ParseMarkdownTool()
    
    # Test relative path
    result_json1 = tool._run(markdown1)
    result1 = json.loads(result_json1)
    assert result1["success"] is True
    reconstructed1 = reconstruct_content_from_segments(result1["segments"])
    assert reconstructed1 == markdown1
    
    # Verify path is protected
    path_protected = False
    for seg in result1["segments"]:
        if seg["content"] == relative_path and seg["type"] == "protected":
            path_protected = True
    assert path_protected, "Relative path should be protected"
    
    # Test anchor link
    result_json2 = tool._run(markdown2)
    result2 = json.loads(result_json2)
    assert result2["success"] is True
    reconstructed2 = reconstruct_content_from_segments(result2["segments"])
    assert reconstructed2 == markdown2
    
    # Verify anchor is protected
    anchor_protected = False
    for seg in result2["segments"]:
        if seg["content"] == anchor and seg["type"] == "protected":
            anchor_protected = True
    assert anchor_protected, "Anchor link should be protected"


@given(
    text1=simple_text_strategy,
    text2=simple_text_strategy,
    code=code_content_strategy,
    url=url_strategy
)
@settings(max_examples=100)
def test_property_complex_markdown_round_trip(text1: str, text2: str, code: str, url: str):
    """
    Property 2: Protected region round-trip (complex case)
    
    For any markdown with multiple protected regions, all regions should be
    preserved byte-identical after parsing.
    Validates: Requirements 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.5
    """
    # Create complex markdown with multiple protected regions
    markdown = f"{text1} `{code}` and [{text2}]({url})"
    
    tool = ParseMarkdownTool()
    result_json = tool._run(markdown)
    result = json.loads(result_json)
    
    assert result["success"] is True
    
    # Reconstruct content from segments
    reconstructed = reconstruct_content_from_segments(result["segments"])
    
    # Content should be identical
    assert reconstructed == markdown
    
    # Verify both protected regions are detected
    inline_code_found = False
    link_url_found = False
    
    for seg in result["segments"]:
        if seg["type"] == "protected":
            if seg["metadata"] and seg["metadata"]["protection_reason"] == "inline-code":
                inline_code_found = True
            if seg["metadata"] and seg["metadata"]["protection_reason"] == "link-url":
                link_url_found = True
    
    assert inline_code_found, "Inline code should be protected"
    assert link_url_found, "Link URL should be protected"


@given(
    lines=st.lists(
        st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P')), min_size=0, max_size=50),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100)
def test_property_structure_preservation(lines: list):
    """
    Property 1: Whitespace preservation (partial test)
    
    For any markdown, structure information should capture line breaks and indentation.
    Validates: Requirements 3.1
    """
    # Create markdown with various line structures
    markdown = '\n'.join(lines)
    
    tool = ParseMarkdownTool()
    result_json = tool._run(markdown)
    result = json.loads(result_json)
    
    assert result["success"] is True
    
    # Verify structure information is captured
    assert "structure" in result
    assert "line_breaks" in result["structure"]
    assert "indentation" in result["structure"]
    assert "whitespace" in result["structure"]
    
    # Reconstruct content
    reconstructed = reconstruct_content_from_segments(result["segments"])
    
    # Content should be identical (including line breaks)
    assert reconstructed == markdown
