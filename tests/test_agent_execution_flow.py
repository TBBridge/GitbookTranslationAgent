"""Tests for agent execution flow."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.agent.translation_agent import TranslationAgent
from src.models import CLIConfig, AgentState


@pytest.fixture
def valid_config():
    """Create a valid CLI configuration for testing."""
    return CLIConfig(
        repo_url="https://github.com/test/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix"
    )


def test_agent_execution_flow_initialization(valid_config):
    """Test that agent execution flow initializes state correctly.
    
    Requirements: All requirements - execution
    """
    agent = TranslationAgent(config=valid_config)
    
    # Verify initial state is created
    assert agent.state is not None
    assert isinstance(agent.state, AgentState)
    assert agent.state.config == valid_config
    assert agent.state.fetched_files == []
    assert agent.state.diff_result is None
    assert agent.state.glossary is None
    assert agent.state.current_file is None
    assert agent.state.current_language is None
    assert agent.state.results == {}
    assert agent.state.errors == []


def test_agent_execution_flow_success(valid_config):
    """Test successful agent execution flow.
    
    Requirements: All requirements - execution
    """
    agent = TranslationAgent(config=valid_config)
    
    # Mock the agent executor to return a successful result
    mock_result = {
        "messages": [
            Mock(content="Translation completed successfully", tool_calls=None)
        ]
    }
    
    with patch.object(agent.agent_executor, 'invoke', return_value=mock_result):
        result = agent.run()
    
    # Verify result structure
    assert result["status"] == "success"
    assert "output" in result
    assert "messages" in result
    assert "intermediate_steps" in result
    assert "correction_loops" in result
    assert "state" in result
    assert "execution_duration" in result
    assert "timestamp" in result
    
    # Verify state information is collected
    assert "fetched_files_count" in result["state"]
    assert "current_file" in result["state"]
    assert "current_language" in result["state"]
    assert "results_count" in result["state"]
    assert "errors_count" in result["state"]


def test_agent_execution_flow_with_tool_calls(valid_config):
    """Test agent execution flow collects tool calls correctly.
    
    Requirements: All requirements - execution
    """
    agent = TranslationAgent(config=valid_config)
    
    # Mock tool calls
    mock_tool_call_1 = {
        "name": "FetchGitHubFilesTool",
        "args": {"repo_url": "https://github.com/test/repo"}
    }
    mock_tool_call_2 = {
        "name": "TranslateContentTool",
        "args": {"content": "test content"}
    }
    
    mock_message_1 = Mock()
    mock_message_1.tool_calls = [mock_tool_call_1]
    mock_message_1.content = "Fetching files..."
    
    mock_message_2 = Mock()
    mock_message_2.tool_calls = [mock_tool_call_2]
    mock_message_2.content = "Translating content..."
    
    mock_message_3 = Mock()
    mock_message_3.tool_calls = None
    mock_message_3.content = "Translation completed"
    
    mock_result = {
        "messages": [mock_message_1, mock_message_2, mock_message_3]
    }
    
    with patch.object(agent.agent_executor, 'invoke', return_value=mock_result):
        result = agent.run()
    
    # Verify intermediate steps are collected
    assert len(result["intermediate_steps"]) == 2
    assert result["intermediate_steps"][0]["tool"] == "FetchGitHubFilesTool"
    assert result["intermediate_steps"][1]["tool"] == "TranslateContentTool"
    
    # Verify tool call count
    assert "tool_call_count" in result
    assert result["tool_call_count"]["FetchGitHubFilesTool"] == 1
    assert result["tool_call_count"]["TranslateContentTool"] == 1


def test_agent_execution_flow_error_handling(valid_config):
    """Test agent execution flow handles errors correctly.
    
    Requirements: All requirements - execution
    """
    agent = TranslationAgent(config=valid_config)
    
    # Mock the agent executor to raise an exception
    with patch.object(agent.agent_executor, 'invoke', side_effect=Exception("Test error")):
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = agent.run()
    
    # Verify error result structure
    assert result["status"] == "error"
    assert "error" in result
    assert "error_type" in result
    assert result["error_type"] == "Exception"
    assert "message" in result
    assert "Test error" in result["message"]
    assert "errors" in result
    assert "execution_duration" in result
    assert "timestamp" in result
    
    # Verify error details are collected
    assert len(result["errors"]) > 0
    assert "error_type" in result["errors"][-1]
    assert "error_message" in result["errors"][-1]


def test_agent_execution_flow_retry_logic(valid_config):
    """Test agent execution flow retries on failure.
    
    Requirements: All requirements - execution
    """
    agent = TranslationAgent(config=valid_config)
    
    # Mock the agent executor to fail twice then succeed
    call_count = 0
    
    def mock_invoke(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception(f"Temporary error {call_count}")
        return {
            "messages": [Mock(content="Success after retries", tool_calls=None)]
        }
    
    with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = agent.run()
    
    # Verify retry logic worked
    assert result["status"] == "success"
    assert result["retry_count"] == 2  # Failed twice before succeeding
    assert "errors" in result
    assert len(result["errors"]) == 2  # Two failed attempts recorded


def test_agent_execution_flow_max_retries_exceeded(valid_config):
    """Test agent execution flow fails after max retries.
    
    Requirements: All requirements - execution
    """
    agent = TranslationAgent(config=valid_config)
    
    # Mock the agent executor to always fail
    with patch.object(agent.agent_executor, 'invoke', side_effect=Exception("Persistent error")):
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = agent.run()
    
    # Verify max retries were attempted
    assert result["status"] == "error"
    assert result["retry_count"] == 4  # 1 initial + 3 retries
    assert "errors" in result
    # The errors list contains retry attempts + final error details
    assert len(result["errors"]) == 5  # 4 retry attempts + 1 final error


def test_agent_execution_flow_sensitive_info_masking(valid_config):
    """Test that sensitive information is masked in execution results.
    
    Requirements: All requirements - safety
    """
    agent = TranslationAgent(config=valid_config)
    
    # Mock result with sensitive information
    mock_message = Mock()
    mock_message.content = "Using token ghp_1234567890123456789012345678901234567890"
    mock_message.tool_calls = None
    
    mock_result = {
        "messages": [mock_message]
    }
    
    with patch.object(agent.agent_executor, 'invoke', return_value=mock_result):
        result = agent.run()
    
    # Verify sensitive info is masked
    assert "ghp_" not in result["output"]
    assert "***GITHUB_TOKEN***" in result["output"]


def test_agent_execution_flow_memory_storage(valid_config):
    """Test that execution flow stores conversation in memory.
    
    Requirements: All requirements - execution
    """
    agent = TranslationAgent(config=valid_config)
    
    mock_result = {
        "messages": [Mock(content="Test output", tool_calls=None)]
    }
    
    with patch.object(agent.agent_executor, 'invoke', return_value=mock_result):
        result = agent.run()
    
    # Verify memory is updated
    assert len(agent.memory) > 0
    assert "input" in agent.memory[0]
    assert "output" in agent.memory[0]
    assert "timestamp" in agent.memory[0]


def test_agent_execution_flow_partial_state_on_error(valid_config):
    """Test that partial state is collected even when execution fails.
    
    Requirements: All requirements - execution
    """
    agent = TranslationAgent(config=valid_config)
    
    # Mock the agent executor to raise an exception after we set state
    def mock_invoke(*args, **kwargs):
        # Set state before raising error
        agent.state.current_file = "test.md"
        agent.state.current_language = "en"
        raise Exception("Test error")
    
    with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = agent.run()
    
    # Verify partial state is collected
    assert result["status"] == "error"
    assert result["state"] is not None
    assert result["state"]["current_file"] == "test.md"
    assert result["state"]["current_language"] == "en"


def test_agent_execution_flow_execution_duration(valid_config):
    """Test that execution duration is tracked.
    
    Requirements: All requirements - execution
    """
    agent = TranslationAgent(config=valid_config)
    
    mock_result = {
        "messages": [Mock(content="Test output", tool_calls=None)]
    }
    
    with patch.object(agent.agent_executor, 'invoke', return_value=mock_result):
        result = agent.run()
    
    # Verify execution duration is tracked
    assert "execution_duration" in result
    assert isinstance(result["execution_duration"], float)
    assert result["execution_duration"] >= 0


def test_agent_execution_flow_timestamp(valid_config):
    """Test that timestamp is included in results.
    
    Requirements: All requirements - execution
    """
    agent = TranslationAgent(config=valid_config)
    
    mock_result = {
        "messages": [Mock(content="Test output", tool_calls=None)]
    }
    
    with patch.object(agent.agent_executor, 'invoke', return_value=mock_result):
        result = agent.run()
    
    # Verify timestamp is included
    assert "timestamp" in result
    assert isinstance(result["timestamp"], str)
    # Verify it's in ISO format (basic check)
    assert "T" in result["timestamp"]
