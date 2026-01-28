"""Unit tests for TranslateContentTool retry logic and error handling."""

import os
import json
import pytest
from unittest.mock import Mock, patch, call
from openai import APITimeoutError, RateLimitError, APIError

from src.tools.translate_content import TranslateContentTool
from src.models.markdown_models import Segment, SegmentType, StructureInfo
from src.models.glossary_models import Glossary
from src.models.translation_models import TranslationRequest


@pytest.fixture
def sample_request():
    """Sample translation request for testing."""
    segments = [
        Segment(
            type=SegmentType.TRANSLATABLE,
            content="これはテストです。",
            start_line=0,
            end_line=0,
            metadata=None
        )
    ]
    
    glossary = Glossary(
        format="auto-detected",
        mappings={}
    )
    
    structure = StructureInfo(
        line_breaks=[],
        indentation={},
        whitespace={}
    )
    
    return TranslationRequest(
        segments=segments,
        target_language="en",
        glossary=glossary,
        structure=structure
    )


@pytest.fixture
def mock_success_response():
    """Mock successful LLM response."""
    mock_response = Mock()
    mock_response.content = "[Segment 1]\nThis is a test."
    return mock_response


def test_retry_on_timeout(sample_request, mock_success_response):
    """Test that tool retries on timeout errors."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    # Mock to fail twice with timeout, then succeed
    with patch.object(
        tool.llm.__class__,
        'invoke',
        side_effect=[
            APITimeoutError("Timeout 1"),
            APITimeoutError("Timeout 2"),
            mock_success_response
        ]
    ):
        result = tool.translate(sample_request)
        
        assert result is not None
        assert result.reconstructed_content is not None
        # Verify it was called 3 times (2 failures + 1 success)
        assert tool.llm.invoke.call_count == 3


def test_retry_on_rate_limit(sample_request, mock_success_response):
    """Test that tool retries on rate limit errors."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    # Mock to fail once with rate limit, then succeed
    # Use a generic Exception since RateLimitError requires complex initialization
    with patch.object(
        tool.llm.__class__,
        'invoke',
        side_effect=[
            Exception("Rate limit exceeded"),
            mock_success_response
        ]
    ):
        result = tool.translate(sample_request)
        
        assert result is not None
        assert result.reconstructed_content is not None
        # Verify it was called 2 times (1 failure + 1 success)
        assert tool.llm.invoke.call_count == 2


def test_retry_on_invalid_response(sample_request, mock_success_response):
    """Test that tool retries on invalid response format."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    # Mock to return empty response first, then valid response
    mock_empty_response = Mock()
    mock_empty_response.content = ""
    
    with patch.object(
        tool.llm.__class__,
        'invoke',
        side_effect=[
            mock_empty_response,
            mock_success_response
        ]
    ):
        result = tool.translate(sample_request)
        
        assert result is not None
        assert result.reconstructed_content is not None
        # Verify it was called 2 times (1 failure + 1 success)
        assert tool.llm.invoke.call_count == 2


def test_max_retries_exceeded_timeout(sample_request):
    """Test that tool fails after max retries on timeout."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    # Mock to always fail with timeout
    with patch.object(
        tool.llm.__class__,
        'invoke',
        side_effect=APITimeoutError("Timeout")
    ):
        with pytest.raises(Exception) as exc_info:
            tool.translate(sample_request)
        
        assert "timeout" in str(exc_info.value).lower()
        # Verify it was called max_manual_retries + 1 times
        assert tool.llm.invoke.call_count == tool.max_manual_retries + 1


def test_max_retries_exceeded_invalid_response(sample_request):
    """Test that tool fails after max retries on invalid response."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    # Mock to always return empty response
    mock_empty_response = Mock()
    mock_empty_response.content = ""
    
    with patch.object(
        tool.llm.__class__,
        'invoke',
        return_value=mock_empty_response
    ):
        with pytest.raises(Exception) as exc_info:
            tool.translate(sample_request)
        
        assert "invalid response format" in str(exc_info.value).lower()
        # Verify it was called max_manual_retries + 1 times
        assert tool.llm.invoke.call_count == tool.max_manual_retries + 1


def test_api_error_retry(sample_request, mock_success_response):
    """Test that tool retries on general API errors."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    # Mock to fail once with API error, then succeed
    # Use a generic Exception since APIError requires complex initialization
    with patch.object(
        tool.llm.__class__,
        'invoke',
        side_effect=[
            Exception("API Error"),
            mock_success_response
        ]
    ):
        result = tool.translate(sample_request)
        
        assert result is not None
        assert result.reconstructed_content is not None
        # Verify it was called 2 times (1 failure + 1 success)
        assert tool.llm.invoke.call_count == 2


def test_no_retry_on_success(sample_request, mock_success_response):
    """Test that tool doesn't retry when first attempt succeeds."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    with patch.object(
        tool.llm.__class__,
        'invoke',
        return_value=mock_success_response
    ):
        result = tool.translate(sample_request)
        
        assert result is not None
        assert result.reconstructed_content is not None
        # Verify it was called only once
        assert tool.llm.invoke.call_count == 1


def test_exponential_backoff_timing(sample_request, mock_success_response):
    """Test that exponential backoff delays are applied correctly."""
    os.environ["OPENAI_API_KEY"] = "test-key"
    tool = TranslateContentTool()
    
    # Mock to fail twice, then succeed
    with patch.object(
        tool.llm.__class__,
        'invoke',
        side_effect=[
            APITimeoutError("Timeout 1"),
            APITimeoutError("Timeout 2"),
            mock_success_response
        ]
    ):
        with patch('time.sleep') as mock_sleep:
            result = tool.translate(sample_request)
            
            assert result is not None
            # Verify sleep was called with exponential backoff
            # First retry: 2^1 = 2 seconds
            # Second retry: 2^2 = 4 seconds
            assert mock_sleep.call_count == 2
            calls = mock_sleep.call_args_list
            assert calls[0] == call(2)  # 2^1
            assert calls[1] == call(4)  # 2^2
