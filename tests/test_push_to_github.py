"""Tests for PushToGitHubTool."""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from src.tools.push_to_github import PushToGitHubTool
from github import GithubException


@pytest.fixture
def push_tool():
    """Create PushToGitHubTool instance."""
    return PushToGitHubTool()


@pytest.fixture
def sample_files():
    """Sample files for testing."""
    return [
        {"path": "docs/intro.md", "content": "# Introduction\n\nThis is the intro."},
        {"path": "docs/guide.md", "content": "# Guide\n\nThis is the guide."}
    ]

def test_parse_repo_url_owner_repo_format(push_tool):
    result = push_tool._parse_repo_url("owner/repo")
    assert result == "owner/repo"

def test_parse_repo_url_full_https(push_tool):
    result = push_tool._parse_repo_url("https://github.com/owner/repo")
    assert result == "owner/repo"

def test_parse_repo_url_invalid(push_tool):
    result = push_tool._parse_repo_url("invalid-url")
    assert result is None

def test_generate_branch_name(push_tool):
    branch_name = push_tool._generate_branch_name("en")
    assert branch_name.startswith("translation/en/")
    assert len(branch_name.split("/")) == 3

def test_format_github_error_401(push_tool):
    error = GithubException(401, {"message": "Bad credentials"})
    result = push_tool._format_github_error(error)
    assert "Authentication failed" in result

def test_format_github_error_404(push_tool):
    error = GithubException(404, {"message": "Not Found"})
    result = push_tool._format_github_error(error)
    assert "Repository or branch not found" in result

@patch('src.tools.push_to_github.Github')
def test_run_no_auth_token(mock_github_class, push_tool, sample_files):
    with patch.dict('os.environ', {}, clear=True):
        result = push_tool._run(
            repo_url="owner/repo",
            branch="main",
            files=sample_files,
            push_option="push_same_repo_new_branch",
            language="en",
            auth_token=None
        )
    data = json.loads(result)
    assert data["success"] is False
    assert "authentication token is required" in data["error"].lower()

@patch('src.tools.push_to_github.Github')
def test_run_invalid_repo_url(mock_github_class, push_tool, sample_files):
    mock_client = Mock()
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    result = push_tool._run(
        repo_url="invalid-url",
        branch="main",
        files=sample_files,
        push_option="push_same_repo_new_branch",
        language="en",
        auth_token="test-token"
    )
    data = json.loads(result)
    assert data["success"] is False
    assert "Invalid repository URL" in data["error"]

@patch('src.tools.push_to_github.Github')
def test_run_authentication_failure(mock_github_class, push_tool, sample_files):
    mock_client = Mock()
    mock_client.get_repo.side_effect = GithubException(401, {"message": "Bad credentials"})
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    result = push_tool._run(
        repo_url="owner/repo",
        branch="main",
        files=sample_files,
        push_option="push_same_repo_new_branch",
        language="en",
        auth_token="invalid-token"
    )
    data = json.loads(result)
    assert data["success"] is False
    assert "Authentication failed" in data["error"]

@patch('src.tools.push_to_github.Github')
def test_push_direct_without_confirmation(mock_github_class, push_tool, sample_files):
    mock_client = Mock()
    mock_repo = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    result = push_tool._run(
        repo_url="owner/repo",
        branch="main",
        files=sample_files,
        push_option="push_same_repo_direct",
        language="en",
        auth_token="test-token",
        user_confirmation=False
    )
    data = json.loads(result)
    assert data["success"] is False
    assert "requires explicit user confirmation" in data["error"]

@patch('src.tools.push_to_github.Github')
def test_push_direct_create_new_file(mock_github_class, push_tool, sample_files):
    mock_client = Mock()
    mock_repo = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    mock_repo.get_contents.side_effect = GithubException(404, {"message": "Not Found"})
    mock_repo.create_file.return_value = Mock()
    result = push_tool._run(
        repo_url="owner/repo",
        branch="main",
        files=sample_files,
        push_option="push_same_repo_direct",
        language="en",
        auth_token="test-token",
        user_confirmation=True
    )
    data = json.loads(result)
    assert data["success"] is True
    assert data["branch_name"] == "main"
    assert mock_repo.create_file.call_count == len(sample_files)

@patch('src.tools.push_to_github.Github')
def test_push_new_branch_create_branch(mock_github_class, push_tool, sample_files):
    mock_client = Mock()
    mock_repo = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    mock_ref = Mock()
    mock_ref.object.sha = "source-sha-123"
    mock_repo.get_git_ref.return_value = mock_ref
    mock_repo.create_git_ref.return_value = Mock()
    mock_repo.get_contents.side_effect = GithubException(404, {"message": "Not Found"})
    mock_repo.create_file.return_value = Mock()
    mock_repo.full_name = "owner/repo"
    result = push_tool._run(
        repo_url="owner/repo",
        branch="main",
        files=sample_files,
        push_option="push_same_repo_new_branch",
        language="en",
        auth_token="test-token"
    )
    data = json.loads(result)
    assert data["success"] is True
    assert data["branch_name"].startswith("translation/en/")
    assert "pr_info" in data
    assert mock_repo.create_git_ref.called
    assert mock_repo.create_file.call_count == len(sample_files)

@patch('src.tools.push_to_github.Github')
def test_push_direct_error_handling(mock_github_class, push_tool, sample_files):
    mock_client = Mock()
    mock_repo = Mock()
    mock_client.get_repo.return_value = mock_repo
    mock_client.close = Mock()
    mock_github_class.return_value = mock_client
    mock_repo.get_contents.side_effect = Exception("Network error")
    result = push_tool._run(
        repo_url="owner/repo",
        branch="main",
        files=sample_files,
        push_option="push_same_repo_direct",
        language="en",
        auth_token="test-token",
        user_confirmation=True
    )
    data = json.loads(result)
    assert data["success"] is False
    assert "Failed to push files" in data["error"]
