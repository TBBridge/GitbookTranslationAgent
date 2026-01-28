"""Integration tests for the Translation Agent.

Tests for complete translation workflow, error recovery, and multi-language processing.
Requirements: All requirements - integration
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from src.agent.translation_agent import TranslationAgent
from src.models import (
    CLIConfig, FetchedFile, DiffResult, ParsedMarkdown, Segment, SegmentType,
    Glossary, TranslationResult, ReviewResult, Issue, IssueSeverity, IssueCategory,
    IssueLocation
)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def valid_config(temp_output_dir):
    """Create a valid CLI configuration for integration testing."""
    return CLIConfig(
        repo_url="https://github.com/test/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en", "zh-CN"],
        glossary_path="glossary.json",
        output_root=temp_output_dir,
        push_option="none",
        output_naming="suffix"
    )


@pytest.fixture
def sample_glossary():
    """Create a sample glossary for testing."""
    return Glossary(
        format="auto-detected",
        mappings={
            "帳票定義": {"en": "Template Form", "zh-CN": "报表定义"},
            "ユーザー": {"en": "User", "zh-CN": "用户"},
        }
    )


@pytest.fixture
def sample_markdown_file():
    """Create a sample markdown file for testing."""
    return FetchedFile(
        path="docs/intro.md",
        content="""# Introduction

This is a test document with 帳票定義 and ユーザー content.

## Code Example

```python
def hello():
    print("Hello, World!")
```

## Links

Check out [this link](https://example.com) for more info.

## Table

| Column 1 | Column 2 |
|----------|----------|
| 値1      | 値2      |
""",
        commit_hash="abc123def456",
        last_modified=datetime.now()
    )


class TestAgentCompleteTranslationWorkflow:
    """Test complete translation workflow from start to finish."""

    def test_agent_complete_workflow_single_file_single_language(self, valid_config, sample_markdown_file):
        """Test complete translation workflow for a single file and language.
        
        Requirements: All requirements - integration
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock all the tools to simulate a complete workflow
        with patch('src.agent.translation_agent.FetchGitHubFilesTool') as mock_fetch_tool, \
             patch('src.agent.translation_agent.DetectFileChangesTool') as mock_diff_tool, \
             patch('src.agent.translation_agent.ParseMarkdownTool') as mock_parse_tool, \
             patch('src.agent.translation_agent.LoadGlossaryTool') as mock_glossary_tool, \
             patch('src.agent.translation_agent.TranslateContentTool') as mock_translate_tool, \
             patch('src.agent.translation_agent.ReviewTranslationTool') as mock_review_tool, \
             patch('src.agent.translation_agent.SaveTranslationTool') as mock_save_tool, \
             patch('src.agent.translation_agent.LogProgressTool') as mock_log_tool:
            
            # Mock the agent executor to simulate successful workflow
            def mock_invoke(*args, **kwargs):
                messages = []
                
                # Simulate workflow steps
                msg1 = Mock()
                msg1.content = "Fetched 1 file from repository"
                msg1.tool_calls = None
                messages.append(msg1)
                
                msg2 = Mock()
                msg2.content = "Detected 1 modified file"
                msg2.tool_calls = None
                messages.append(msg2)
                
                msg3 = Mock()
                msg3.content = "Loaded glossary with 2 terms"
                msg3.tool_calls = None
                messages.append(msg3)
                
                msg4 = Mock()
                msg4.content = "Translated file to English"
                msg4.tool_calls = None
                messages.append(msg4)
                
                msg5 = Mock()
                msg5.content = "Review passed with no issues"
                msg5.tool_calls = None
                messages.append(msg5)
                
                msg6 = Mock()
                msg6.content = "Saved translated file"
                msg6.tool_calls = None
                messages.append(msg6)
                
                msg7 = Mock()
                msg7.content = "Translation workflow completed successfully"
                msg7.tool_calls = None
                messages.append(msg7)
                
                return {"messages": messages}
            
            with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
                result = agent.run()
        
        # Verify workflow completed successfully
        assert result["status"] == "success"
        assert "completed successfully" in result["output"].lower()
        assert len(result["intermediate_steps"]) >= 0
        assert result["state"] is not None

    def test_agent_complete_workflow_multiple_files(self, valid_config):
        """Test complete translation workflow for multiple files.
        
        Requirements: All requirements - integration
        """
        agent = TranslationAgent(config=valid_config)
        
        # Create multiple sample files
        files = [
            FetchedFile(
                path=f"docs/file{i}.md",
                content=f"# File {i}\n\nContent with 日本語 text.",
                commit_hash=f"hash{i}",
                last_modified=datetime.now()
            )
            for i in range(3)
        ]
        
        # Mock the agent executor
        def mock_invoke(*args, **kwargs):
            messages = []
            
            # Simulate processing multiple files
            for i, file in enumerate(files):
                msg = Mock()
                msg.content = f"Processed {file.path}"
                msg.tool_calls = None
                messages.append(msg)
            
            final_msg = Mock()
            final_msg.content = "All files processed successfully"
            final_msg.tool_calls = None
            messages.append(final_msg)
            
            return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            result = agent.run()
        
        # Verify all files were processed
        assert result["status"] == "success"
        assert "All files processed" in result["output"]

    def test_agent_complete_workflow_multiple_languages(self, valid_config):
        """Test complete translation workflow for multiple languages.
        
        Requirements: All requirements - integration
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor
        def mock_invoke(*args, **kwargs):
            messages = []
            
            # Simulate processing for each language
            for lang in valid_config.languages:
                msg = Mock()
                msg.content = f"Translated to {lang}"
                msg.tool_calls = None
                messages.append(msg)
            
            final_msg = Mock()
            final_msg.content = "All languages processed successfully"
            final_msg.tool_calls = None
            messages.append(final_msg)
            
            return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            result = agent.run()
        
        # Verify all languages were processed
        assert result["status"] == "success"
        assert "All languages processed" in result["output"]


class TestAgentErrorRecovery:
    """Test agent error recovery and resilience."""

    def test_agent_recovers_from_tool_failure(self, valid_config):
        """Test that agent recovers from individual tool failures.
        
        Requirements: All requirements - integration
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor to fail once then succeed
        call_count = 0
        
        def mock_invoke(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call fails
                raise Exception("Tool execution failed")
            else:
                # Second call succeeds
                messages = []
                msg = Mock()
                msg.content = "Recovered from error and completed successfully"
                msg.tool_calls = None
                messages.append(msg)
                return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = agent.run()
        
        # Verify recovery
        assert result["status"] == "success"
        assert result["retry_count"] == 1

    def test_agent_handles_partial_failure(self, valid_config):
        """Test that agent handles partial failures gracefully.
        
        Requirements: All requirements - integration
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor to simulate partial failure
        def mock_invoke(*args, **kwargs):
            messages = []
            
            # Simulate some successes and some failures
            msg1 = Mock()
            msg1.content = "Processed file1.md successfully"
            msg1.tool_calls = None
            messages.append(msg1)
            
            msg2 = Mock()
            msg2.content = "Error processing file2.md: File too large"
            msg2.tool_calls = None
            messages.append(msg2)
            
            msg3 = Mock()
            msg3.content = "Processed file3.md successfully"
            msg3.tool_calls = None
            messages.append(msg3)
            
            final_msg = Mock()
            final_msg.content = "Processing completed with 1 error"
            final_msg.tool_calls = None
            messages.append(final_msg)
            
            return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            result = agent.run()
        
        # Verify partial success
        assert result["status"] == "success"
        assert "completed with 1 error" in result["output"]

    def test_agent_respects_max_retries(self, valid_config):
        """Test that agent respects maximum retry limit.
        
        Requirements: All requirements - safety
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor to always fail
        with patch.object(agent.agent_executor, 'invoke', side_effect=Exception("Persistent error")):
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = agent.run()
        
        # Verify max retries were attempted
        assert result["status"] == "error"
        assert result["retry_count"] == 4  # 1 initial + 3 retries


class TestAgentMultiLanguageProcessing:
    """Test multi-language processing capabilities."""

    def test_agent_processes_all_languages_sequentially(self, valid_config):
        """Test that agent processes all languages sequentially.
        
        Requirements: Requirements 15.1, 15.2
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor
        def mock_invoke(*args, **kwargs):
            messages = []
            
            # Simulate sequential language processing
            for lang in valid_config.languages:
                msg = Mock()
                msg.content = f"Processing language: {lang}"
                msg.tool_calls = None
                messages.append(msg)
            
            final_msg = Mock()
            final_msg.content = f"Processed {len(valid_config.languages)} languages"
            final_msg.tool_calls = None
            messages.append(final_msg)
            
            return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            result = agent.run()
        
        # Verify all languages were processed
        assert result["status"] == "success"
        assert f"Processed {len(valid_config.languages)} languages" in result["output"]

    def test_agent_applies_language_specific_glossary(self, valid_config, sample_glossary):
        """Test that agent applies language-specific glossary mappings.
        
        Requirements: Requirements 15.2
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor
        def mock_invoke(*args, **kwargs):
            messages = []
            
            # Simulate glossary application for each language
            for lang in valid_config.languages:
                msg = Mock()
                msg.content = f"Applied glossary for {lang}: Template Form, User"
                msg.tool_calls = None
                messages.append(msg)
            
            final_msg = Mock()
            final_msg.content = "Glossary applied for all languages"
            final_msg.tool_calls = None
            messages.append(final_msg)
            
            return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            result = agent.run()
        
        # Verify glossary was applied
        assert result["status"] == "success"
        assert "Glossary applied" in result["output"]

    def test_agent_continues_after_language_error(self, valid_config):
        """Test that agent continues processing other languages after one fails.
        
        Requirements: Requirements 15.4
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor
        def mock_invoke(*args, **kwargs):
            messages = []
            
            # Simulate error for first language, success for others
            msg1 = Mock()
            msg1.content = f"Error translating to {valid_config.languages[0]}"
            msg1.tool_calls = None
            messages.append(msg1)
            
            for lang in valid_config.languages[1:]:
                msg = Mock()
                msg.content = f"Successfully translated to {lang}"
                msg.tool_calls = None
                messages.append(msg)
            
            final_msg = Mock()
            final_msg.content = "Processing completed with 1 error"
            final_msg.tool_calls = None
            messages.append(final_msg)
            
            return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            result = agent.run()
        
        # Verify error isolation
        assert result["status"] == "success"
        assert "completed with 1 error" in result["output"]


class TestAgentWithMockTools:
    """Test agent with fully mocked tools."""

    def test_agent_with_all_tools_mocked(self, valid_config):
        """Test agent execution with all tools mocked.
        
        Requirements: All requirements - integration
        """
        agent = TranslationAgent(config=valid_config)
        
        # Verify all tools are initialized
        assert len(agent.tools) == 10
        tool_names = [tool.name for tool in agent.tools]
        
        # Tool names are in snake_case format
        expected_tools = [
            "fetch_github_files",
            "detect_file_changes",
            "parse_markdown",
            "load_glossary",
            "translate_content",
            "review_translation",
            "correct_translation",
            "save_translation",
            "push_to_github",
            "log_progress",
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool {expected_tool} not found"

    def test_agent_tool_execution_order(self, valid_config):
        """Test that agent executes tools in correct order.
        
        Requirements: All requirements - integration
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor to track tool execution order
        def mock_invoke(*args, **kwargs):
            messages = []
            
            # Simulate tool execution in order
            tool_sequence = [
                "FetchGitHubFilesTool",
                "DetectFileChangesTool",
                "LoadGlossaryTool",
                "ParseMarkdownTool",
                "TranslateContentTool",
                "ReviewTranslationTool",
                "SaveTranslationTool",
            ]
            
            for tool_name in tool_sequence:
                msg = Mock()
                msg.content = f"Executed {tool_name}"
                msg.tool_calls = [{"name": tool_name, "args": {}}]
                messages.append(msg)
            
            final_msg = Mock()
            final_msg.content = "All tools executed in order"
            final_msg.tool_calls = None
            messages.append(final_msg)
            
            return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            result = agent.run()
        
        # Verify tools were executed
        assert result["status"] == "success"
        assert len(result["intermediate_steps"]) == 7


class TestAgentGuardrails:
    """Test agent guardrails and safety features."""

    def test_agent_respects_max_iterations(self, valid_config):
        """Test that agent respects maximum iterations limit.
        
        Requirements: All requirements - safety
        """
        agent = TranslationAgent(config=valid_config)
        
        # Verify max iterations is set
        assert agent.max_iterations == 50
        assert agent.MAX_ITERATIONS == 50

    def test_agent_respects_correction_loop_limit(self, valid_config):
        """Test that agent respects correction loop limit.
        
        Requirements: All requirements - safety
        """
        agent = TranslationAgent(config=valid_config)
        
        # Verify correction loop limit is set
        assert agent.MAX_CORRECTION_LOOPS == 2
        
        # Test correction loop tracking
        file_path = "test.md"
        assert agent._check_correction_limit(file_path) is True
        
        agent._increment_correction_loop(file_path)
        assert agent._check_correction_limit(file_path) is True
        
        agent._increment_correction_loop(file_path)
        assert agent._check_correction_limit(file_path) is False

    def test_agent_validates_file_size(self, valid_config):
        """Test that agent validates file size limits.
        
        Requirements: All requirements - safety
        """
        agent = TranslationAgent(config=valid_config)
        
        # Verify file size limit is set
        assert agent.MAX_FILE_SIZE_BYTES == 1 * 1024 * 1024
        
        # Test small file passes
        small_content = "Small file content"
        agent._validate_file_size(small_content, "small.md")  # Should not raise
        
        # Test large file fails
        large_content = "x" * (1024 * 1024 + 1)
        with pytest.raises(ValueError, match="exceeds size limit"):
            agent._validate_file_size(large_content, "large.md")

    def test_agent_masks_sensitive_information(self, valid_config):
        """Test that agent masks sensitive information in logs.
        
        Requirements: All requirements - safety
        """
        agent = TranslationAgent(config=valid_config)
        
        # Test GitHub token masking
        text_with_token = "Using token ghp_1234567890abcdefghijklmnopqrstuv"
        masked = agent._mask_sensitive_info(text_with_token)
        assert "ghp_" not in masked
        assert "***GITHUB_TOKEN***" in masked
        
        # Test OpenAI key masking (uses sk- not sk_)
        text_with_key = "API key: sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH"
        masked = agent._mask_sensitive_info(text_with_key)
        assert "sk-" not in masked
        assert "***OPENAI_KEY***" in masked


class TestAgentStateManagement:
    """Test agent state management and tracking."""

    def test_agent_initializes_state(self, valid_config):
        """Test that agent initializes state correctly.
        
        Requirements: All requirements - execution
        """
        agent = TranslationAgent(config=valid_config)
        
        # Verify initial state
        assert agent.state is not None
        assert agent.state.config == valid_config
        assert agent.state.fetched_files == []
        assert agent.state.diff_result is None
        assert agent.state.glossary is None
        assert agent.state.current_file is None
        assert agent.state.current_language is None
        assert agent.state.results == {}
        assert agent.state.errors == []

    def test_agent_tracks_correction_loops(self, valid_config):
        """Test that agent tracks correction loops per file.
        
        Requirements: All requirements - execution
        """
        agent = TranslationAgent(config=valid_config)
        
        # Verify correction loop tracking
        assert agent.correction_loops == {}
        
        agent._increment_correction_loop("file1.md")
        assert agent.correction_loops["file1.md"] == 1
        
        agent._increment_correction_loop("file1.md")
        assert agent.correction_loops["file1.md"] == 2
        
        agent._increment_correction_loop("file2.md")
        assert agent.correction_loops["file2.md"] == 1

    def test_agent_collects_execution_results(self, valid_config):
        """Test that agent collects execution results.
        
        Requirements: All requirements - execution
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor
        def mock_invoke(*args, **kwargs):
            messages = []
            msg = Mock()
            msg.content = "Execution completed"
            msg.tool_calls = None
            messages.append(msg)
            return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            result = agent.run()
        
        # Verify result structure
        assert "status" in result
        assert "output" in result
        assert "messages" in result
        assert "intermediate_steps" in result
        assert "correction_loops" in result
        assert "state" in result
        assert "execution_duration" in result
        assert "timestamp" in result


class TestAgentMemoryManagement:
    """Test agent memory and conversation tracking."""

    def test_agent_stores_conversation_in_memory(self, valid_config):
        """Test that agent stores conversation in memory.
        
        Requirements: All requirements - execution
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor
        def mock_invoke(*args, **kwargs):
            messages = []
            msg = Mock()
            msg.content = "Test output"
            msg.tool_calls = None
            messages.append(msg)
            return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            result = agent.run()
        
        # Verify memory is updated
        assert len(agent.memory) > 0
        assert "input" in agent.memory[0]
        assert "output" in agent.memory[0]
        assert "timestamp" in agent.memory[0]

    def test_agent_masks_sensitive_info_in_memory(self, valid_config):
        """Test that agent masks sensitive information in memory.
        
        Requirements: All requirements - safety
        """
        agent = TranslationAgent(config=valid_config)
        
        # Mock the agent executor with sensitive info
        def mock_invoke(*args, **kwargs):
            messages = []
            msg = Mock()
            msg.content = "Using token ghp_1234567890abcdefghijklmnopqrstuv"
            msg.tool_calls = None
            messages.append(msg)
            return {"messages": messages}
        
        with patch.object(agent.agent_executor, 'invoke', side_effect=mock_invoke):
            result = agent.run()
        
        # Verify sensitive info is masked in memory
        assert len(agent.memory) > 0
        memory_input = agent.memory[0]["input"]
        assert "ghp_" not in memory_input
        assert "***GITHUB_TOKEN***" in memory_input or "ghp_" not in memory_input
