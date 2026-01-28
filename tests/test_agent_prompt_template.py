"""Tests for agent prompt template."""

import pytest
from src.agent.translation_agent import AGENT_SYSTEM_PROMPT, TranslationAgent
from src.models import CLIConfig


def test_agent_prompt_template_structure():
    """Test that the agent prompt template contains all required sections."""
    # Verify MISSION section exists
    assert "MISSION:" in AGENT_SYSTEM_PROMPT
    
    # Verify CONFIGURATION section exists
    assert "CONFIGURATION:" in AGENT_SYSTEM_PROMPT
    assert "{repo_url}" in AGENT_SYSTEM_PROMPT
    assert "{branch}" in AGENT_SYSTEM_PROMPT
    assert "{target_paths}" in AGENT_SYSTEM_PROMPT
    assert "{languages}" in AGENT_SYSTEM_PROMPT
    assert "{glossary_path}" in AGENT_SYSTEM_PROMPT
    assert "{output_root}" in AGENT_SYSTEM_PROMPT
    assert "{output_naming}" in AGENT_SYSTEM_PROMPT
    assert "{push_option}" in AGENT_SYSTEM_PROMPT
    
    # Verify CRITICAL RULES section exists
    assert "CRITICAL RULES:" in AGENT_SYSTEM_PROMPT
    assert "FORMAT PRESERVATION IS PARAMOUNT" in AGENT_SYSTEM_PROMPT
    assert "TRANSLATE ONLY JAPANESE TEXT" in AGENT_SYSTEM_PROMPT
    assert "PROTECT SPECIAL REGIONS" in AGENT_SYSTEM_PROMPT
    assert "APPLY GLOSSARY CONSISTENTLY" in AGENT_SYSTEM_PROMPT
    
    # Verify WORKFLOW section exists
    assert "WORKFLOW:" in AGENT_SYSTEM_PROMPT
    assert "FetchGitHubFilesTool" in AGENT_SYSTEM_PROMPT
    assert "DetectFileChangesTool" in AGENT_SYSTEM_PROMPT
    assert "ParseMarkdownTool" in AGENT_SYSTEM_PROMPT
    assert "TranslateContentTool" in AGENT_SYSTEM_PROMPT
    assert "ReviewTranslationTool" in AGENT_SYSTEM_PROMPT
    assert "CorrectTranslationTool" in AGENT_SYSTEM_PROMPT
    assert "SaveTranslationTool" in AGENT_SYSTEM_PROMPT
    
    # Verify GUARDRAILS section exists
    assert "GUARDRAILS:" in AGENT_SYSTEM_PROMPT
    assert "Maximum iterations: 50" in AGENT_SYSTEM_PROMPT
    assert "Maximum correction loops per file: 2" in AGENT_SYSTEM_PROMPT


def test_agent_initialization_with_prompt():
    """Test that TranslationAgent initializes with the prompt template."""
    config = CLIConfig(
        repo_url="https://github.com/test/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix"
    )
    
    agent = TranslationAgent(config=config)
    
    # Verify prompt template is initialized
    assert agent.prompt is not None
    
    # Verify agent and agent_executor are initialized
    assert agent.agent is not None
    assert agent.agent_executor is not None
    
    # Verify tools are initialized (should have 10 tools)
    assert len(agent.tools) == 10
    
    # Verify LLM is initialized
    assert agent.llm is not None


def test_agent_prompt_format():
    """Test that the prompt template can be formatted with configuration."""
    config = CLIConfig(
        repo_url="https://github.com/test/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en", "zh-CN"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix"
    )
    
    agent = TranslationAgent(config=config)
    
    # Format the prompt with sample data
    formatted = agent.prompt.format(
        input="Translate the documentation",
        agent_scratchpad=[]
    )
    
    # Verify configuration values are in the formatted prompt
    assert config.repo_url in formatted
    assert config.branch in formatted
    assert config.glossary_path in formatted
    assert config.output_root in formatted
    
    # Verify no unformatted placeholders remain
    assert "{repo_url}" not in formatted
    assert "{branch}" not in formatted
    assert "{glossary_path}" not in formatted


def test_agent_prompt_contains_requirements():
    """Test that the prompt template addresses key requirements."""
    # Requirement 3.1: Format preservation
    assert "line breaks" in AGENT_SYSTEM_PROMPT
    assert "indentation" in AGENT_SYSTEM_PROMPT
    assert "spacing" in AGENT_SYSTEM_PROMPT
    
    # Requirement 4.1, 4.2: Protected regions
    assert "code blocks" in AGENT_SYSTEM_PROMPT
    assert "inline code" in AGENT_SYSTEM_PROMPT
    
    # Requirement 5.1, 5.2: Links and images
    assert "URLs" in AGENT_SYSTEM_PROMPT
    
    # Requirement 7.1-7.4: Japanese-only translation
    assert "Japanese" in AGENT_SYSTEM_PROMPT
    
    # Requirement 8.3, 8.4: Glossary consistency
    assert "glossary" in AGENT_SYSTEM_PROMPT.lower()
    
    # Requirement 12.1-12.5: Correction loop
    assert "2" in AGENT_SYSTEM_PROMPT  # Max 2 correction iterations
    
    # Requirement 15.4: Error isolation
    assert "continue processing" in AGENT_SYSTEM_PROMPT.lower()
    
    # Requirement 16.1, 16.2: Logging
    assert "Log" in AGENT_SYSTEM_PROMPT
