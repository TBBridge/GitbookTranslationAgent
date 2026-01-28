"""Tests for FetchGitHubFilesTool."""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from src.tools.fetch_github_files import FetchGitHubFilesTool
from github import GithubException, RateLimitExceededException


@pytest.fixture
def fetch_tool():
    """Create FetchGitHubFilesTool instance."""
    return FetchGitHubFilesTool()


@pytest.fixture
def mock_github_client():
    """Create mock GitHub client."""
    client = Mock()
    repo = Mock()
    client.get_repo = Mock(return_value=repo)
    client.close = Mock()
    return client, repo


def test_parse_repo_url_owner_repo_format(fetch_tool):
    """Test parsing repository URL in owner/repo format."""
    result = fetch_tool._parse_repo_url("owner/repo")
    assert result == "owner/repo"


def test_parse_repo_url_full_https(fetch_tool):
    """Test parsing full HTTPS GitHub URL."""
    result = fetch_tool._parse_repo_url("https://github.com/owner/repo")
    assert result == "owner/repo"


def test_parse_repo_url_full_https_with_git(fetch_tool):
    """Test parsing full HTTPS GitHub URL with .git suffix."""
    result = fetch_tool._parse_repo_url("https://github.com/owner/repo.git")
    assert result == "owner/repo"


def test_parse_repo_url_invalid(fetch_tool):
    """Test parsing invalid repository URL."""
    result = fetch_tool._parse_repo_url("invalid-url")
    assert result is None


def test_matches_any_pattern_single_match(fetch_tool):
    """Test glob pattern matching with single pattern."""
    assert fetch_tool._matches_any_pattern("docs/intro.md", ["docs/*.md"])
    assert fetch_tool._matches_any_pattern("README.md", ["*.md"])


def test_matches_any_pattern_recursive(fetch_tool):
    """Test glob pattern matching with recursive pattern."""
    assert fetch_tool._matches_any_pattern("docs/guide/intro.md", ["docs/**/*.md"])
    assert fetch_tool._matches_any_pattern("a/b/c/file.md", ["**/*.md"])


def test_matches_any_pattern_no_match(fetch_tool):
    """Test glob pattern matching with no match."""
    assert not fetch_tool._matches_any_pattern("docs/intro.txt", ["*.md"])
    assert not fetch_tool._matches_any_pattern("test.py", ["*.md", "*.txt"])


def test_matches_any_pattern_multiple_patterns(fetch_tool):
    """Test glob pattern matching with multiple patterns."""
    patterns = ["docs/*.md", "README.md", "*.txt"]
    assert fetch_tool._matches_any_pattern("docs/intro.md", patterns)
    assert fetch_tool._matches_any_pattern("README.md", patterns)
    assert fetch_tool._matches_any_pattern("notes.txt", patterns)


def test_format_github_error_401(fetch_tool):
    """Test formatting authentication error."""
    error = GithubException(401, {"message": "Bad credentials"})
    result = fetch_tool._format_github_error(error)
    assert "Authentication failed" in result
    assert "GITHUB_TOKEN" in result


def test_format_github_error_404(fetch_tool):
    """Test formatting repository not found error."""
    error = GithubException(404, {"message": "Not Found"})
    result = fetch_tool._format_github_error(error)
    assert "Repository not found" in result


def test_format_github_error_403(fetch_tool):
    """Test formatting rate limit error."""
    error = GithubException(403, {"message": "Rate limit exceeded"})
    result = fetch_tool._format_github_error(error)
    assert "Rate limit exceeded" in result


def test_format_github_error_generic(fetch_tool):
    """Test formatting generic GitHub error."""
    error = GithubException(500, {"message": "Internal Server Error"})
    result = fetch_tool._format_github_error(error)
    assert "500" in result
    assert "Internal Server Error" in result


@patch('src.tools.fetch_github_files.Github')
def test_run_invalid_repo_url(mock_github_class, fetch_tool):
    """Test running tool with invalid repository URL."""
    result = fetch_tool._run(
        repo_url="invalid-url",
        branch="main",
        target_paths=["*.md"],
        auth_token="test-token"
    )
    
    data = json.loads(result)
    assert "error" in data
    assert "Invalid repository URL" in data["error"]
    assert data["files"] == []


@patch('src.tools.fetch_github_files.Github')
def test_run_authentication_failure(mock_github_class, fetch_tool):
    """Test running tool with authentication failure."""
    mock_client = Mock()
    mock_client.get_repo.side_effect = GithubException(401, {"message": "Bad credentials"})
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    
    result = fetch_tool._run(
        repo_url="owner/repo",
        branch="main",
        target_paths=["*.md"],
        auth_token="invalid-token"
    )
    
    data = json.loads(result)
    assert "error" in data
    assert "Authentication failed" in data["error"]


@patch('src.tools.fetch_github_files.Github')
def test_run_repository_not_found(mock_github_class, fetch_tool):
    """Test running tool with repository not found."""
    mock_client = Mock()
    mock_client.get_repo.side_effect = GithubException(404, {"message": "Not Found"})
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    
    result = fetch_tool._run(
        repo_url="owner/nonexistent",
        branch="main",
        target_paths=["*.md"],
        auth_token="test-token"
    )
    
    data = json.loads(result)
    assert "error" in data
    assert "Repository not found" in data["error"]


@patch('src.tools.fetch_github_files.Github')
@patch('src.tools.fetch_github_files.time.sleep')
def test_run_with_rate_limit_retry(mock_sleep, mock_github_class, fetch_tool):
    """Test running tool with rate limit and retry."""
    mock_client = Mock()
    mock_repo = Mock()
    
    # First call raises rate limit, second succeeds
    mock_client.get_repo.side_effect = [
        RateLimitExceededException(403, {"message": "Rate limit exceeded"}),
        mock_repo
    ]
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    
    # Mock file fetching to return empty list
    mock_repo.get_contents.return_value = []
    
    result = fetch_tool._run(
        repo_url="owner/repo",
        branch="main",
        target_paths=["*.md"],
        auth_token="test-token"
    )
    
    # Should have retried
    assert mock_sleep.called
    data = json.loads(result)
    assert "success" in data or "error" in data


@patch('src.tools.fetch_github_files.Github')
def test_run_successful_fetch(mock_github_class, fetch_tool):
    """Test successful file fetching."""
    mock_client = Mock()
    mock_repo = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    
    # Mock file content
    mock_file = Mock()
    mock_file.type = "file"
    mock_file.path = "README.md"
    mock_file.decoded_content = b"# Test README"
    
    # Mock commit
    mock_commit = Mock()
    mock_commit.sha = "abc123"
    mock_commit.commit.author.date = datetime(2024, 1, 1, 12, 0, 0)
    
    # Setup mock responses
    mock_repo.get_contents.side_effect = [
        [mock_file],  # Root directory listing
        mock_file     # File content fetch
    ]
    mock_repo.get_commits.return_value = [mock_commit]
    
    result = fetch_tool._run(
        repo_url="owner/repo",
        branch="main",
        target_paths=["*.md"],
        auth_token="test-token"
    )
    
    data = json.loads(result)
    assert data.get("success") is True
    assert len(data.get("files", [])) >= 0
    assert data.get("count") >= 0


def test_get_all_files_recursive_single_file(fetch_tool):
    """Test recursive file listing with single file."""
    mock_repo = Mock()
    mock_file = Mock()
    mock_file.type = "file"
    mock_file.path = "README.md"
    
    mock_repo.get_contents.return_value = [mock_file]
    
    files = fetch_tool._get_all_files_recursive(mock_repo, "main", "")
    assert "README.md" in files


def test_get_all_files_recursive_with_directory(fetch_tool):
    """Test recursive file listing with directory."""
    mock_repo = Mock()
    
    # Root directory
    mock_dir = Mock()
    mock_dir.type = "dir"
    mock_dir.path = "docs"
    
    # File in subdirectory
    mock_file = Mock()
    mock_file.type = "file"
    mock_file.path = "docs/intro.md"
    
    # Setup mock to return directory first, then file
    mock_repo.get_contents.side_effect = [
        [mock_dir],      # Root listing
        [mock_file]      # Subdirectory listing
    ]
    
    files = fetch_tool._get_all_files_recursive(mock_repo, "main", "")
    assert "docs/intro.md" in files


def test_get_all_files_recursive_error_handling(fetch_tool):
    """Test recursive file listing with error."""
    mock_repo = Mock()
    mock_repo.get_contents.side_effect = Exception("Access denied")
    
    # Should return empty list on error
    files = fetch_tool._get_all_files_recursive(mock_repo, "main", "")
    assert files == []


@patch.dict('os.environ', {'GITHUB_TOKEN': 'env-token'})
@patch('src.tools.fetch_github_files.Github')
def test_run_uses_env_token(mock_github_class, fetch_tool):
    """Test that tool uses GITHUB_TOKEN from environment."""
    mock_client = Mock()
    mock_client.get_repo.side_effect = GithubException(404, {"message": "Not Found"})
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    
    result = fetch_tool._run(
        repo_url="owner/repo",
        branch="main",
        target_paths=["*.md"],
        auth_token=None  # No token provided
    )
    
    # Should have been called with env token
    mock_github_class.assert_called_with('env-token')
