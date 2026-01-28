"""Tests for agent guardrails and safety features."""

import pytest
from src.agent.translation_agent import TranslationAgent
from src.models.config import CLIConfig


def test_max_iterations_limit():
    """Test that MAX_ITERATIONS is set to 50."""
    assert TranslationAgent.MAX_ITERATIONS == 50


def test_max_correction_loops_limit():
    """Test that MAX_CORRECTION_LOOPS is set to 2."""
    assert TranslationAgent.MAX_CORRECTION_LOOPS == 2


def test_file_size_limit():
    """Test that MAX_FILE_SIZE_BYTES is set to 1MB."""
    assert TranslationAgent.MAX_FILE_SIZE_BYTES == 1 * 1024 * 1024


def test_translation_timeout():
    """Test that TRANSLATION_TIMEOUT_SECONDS is set to 5 minutes."""
    assert TranslationAgent.TRANSLATION_TIMEOUT_SECONDS == 300


def test_validate_config_valid():
    """Test that valid configuration passes validation."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en", "zh-CN"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    assert agent.config == config


def test_validate_config_invalid_repo_url():
    """Test that invalid repo URL raises ValueError."""
    with pytest.raises(ValueError, match="Only GitHub URLs are supported"):
        config = CLIConfig(
            repo_url="not-a-github-url",
            branch="main",
            target_paths=["docs/**/*.md"],
            languages=["en"],
            glossary_path="glossary.json",
            output_root="output",
            push_option="none",
            output_naming="suffix",
        )


def test_validate_config_path_traversal_in_branch():
    """Test that path traversal in branch name raises ValueError."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="../malicious",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    with pytest.raises(ValueError, match="Invalid branch name"):
        TranslationAgent(config)


def test_validate_config_path_traversal_in_target_paths():
    """Test that path traversal in target paths raises ValueError."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["../../etc/passwd"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    with pytest.raises(ValueError, match="Invalid target path"):
        TranslationAgent(config)


def test_validate_config_invalid_language_code():
    """Test that invalid language code raises ValueError."""
    with pytest.raises(ValueError, match="Invalid language code format"):
        config = CLIConfig(
            repo_url="https://github.com/owner/repo",
            branch="main",
            target_paths=["docs/**/*.md"],
            languages=["invalid-lang-code"],
            glossary_path="glossary.json",
            output_root="output",
            push_option="none",
            output_naming="suffix",
        )


def test_validate_config_path_traversal_in_glossary_path():
    """Test that path traversal in glossary path raises ValueError."""
    with pytest.raises(ValueError, match="Glossary file not found"):
        config = CLIConfig(
            repo_url="https://github.com/owner/repo",
            branch="main",
            target_paths=["docs/**/*.md"],
            languages=["en"],
            glossary_path="../../../etc/passwd",
            output_root="output",
            push_option="none",
            output_naming="suffix",
        )


def test_validate_config_path_traversal_in_output_root():
    """Test that path traversal in output root raises ValueError."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="../../../tmp",
        push_option="none",
        output_naming="suffix",
    )
    with pytest.raises(ValueError, match="Invalid output root"):
        TranslationAgent(config)


def test_validate_config_invalid_push_option():
    """Test that invalid push option raises ValueError."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="invalid_option",
        output_naming="suffix",
    )
    with pytest.raises(ValueError, match="Invalid push_option"):
        TranslationAgent(config)


def test_validate_config_invalid_output_naming():
    """Test that invalid output naming raises ValueError."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="invalid_naming",
    )
    with pytest.raises(ValueError, match="Invalid output_naming"):
        TranslationAgent(config)


def test_sanitize_path_valid():
    """Test that valid paths are sanitized correctly."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    sanitized = agent._sanitize_path("docs/intro.md")
    assert ".." not in sanitized


def test_sanitize_path_traversal_attack():
    """Test that path traversal attempts are blocked."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    with pytest.raises(ValueError, match="Path traversal detected"):
        agent._sanitize_path("../../etc/passwd")


def test_sanitize_path_absolute_path():
    """Test that absolute paths are rejected."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    with pytest.raises(ValueError, match="Absolute paths not allowed"):
        agent._sanitize_path("/etc/passwd")


def test_validate_file_size_within_limit():
    """Test that files within size limit pass validation."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    content = "Small file content"
    agent._validate_file_size(content, "test.md")  # Should not raise


def test_validate_file_size_exceeds_limit():
    """Test that files exceeding size limit raise ValueError."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    # Create content larger than 1MB
    content = "x" * (1024 * 1024 + 1)
    with pytest.raises(ValueError, match="exceeds size limit"):
        agent._validate_file_size(content, "large.md")


def test_check_correction_limit_initial():
    """Test that correction is allowed initially."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    assert agent._check_correction_limit("test.md") is True


def test_check_correction_limit_after_max_loops():
    """Test that correction is blocked after max loops."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    # Increment to max loops
    agent._increment_correction_loop("test.md")
    agent._increment_correction_loop("test.md")
    assert agent._check_correction_limit("test.md") is False


def test_increment_correction_loop():
    """Test that correction loop counter increments correctly."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    assert agent.correction_loops.get("test.md", 0) == 0
    agent._increment_correction_loop("test.md")
    assert agent.correction_loops["test.md"] == 1
    agent._increment_correction_loop("test.md")
    assert agent.correction_loops["test.md"] == 2


def test_mask_sensitive_info_github_token():
    """Test that GitHub tokens are masked."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    text = "Using token ghp_1234567890abcdefghijklmnopqrstuv"
    masked = agent._mask_sensitive_info(text)
    assert "ghp_" not in masked
    assert "***GITHUB_TOKEN***" in masked


def test_mask_sensitive_info_openai_key():
    """Test that OpenAI keys are masked."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    text = "API key: sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH"
    masked = agent._mask_sensitive_info(text)
    assert "sk-" not in masked
    assert "***OPENAI_KEY***" in masked


def test_mask_sensitive_info_bearer_token():
    """Test that Bearer tokens are masked."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    text = "Authorization: Bearer abc123xyz"
    masked = agent._mask_sensitive_info(text)
    assert "abc123xyz" not in masked
    assert "Bearer ***TOKEN***" in masked


def test_mask_sensitive_info_generic_token():
    """Test that generic tokens are masked."""
    config = CLIConfig(
        repo_url="https://github.com/owner/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"],
        glossary_path="glossary.json",
        output_root="output",
        push_option="none",
        output_naming="suffix",
    )
    agent = TranslationAgent(config)
    text = 'token: "secret123"'
    masked = agent._mask_sensitive_info(text)
    assert "secret123" not in masked
    assert "***TOKEN***" in masked
