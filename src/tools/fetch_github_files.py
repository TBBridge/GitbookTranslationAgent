"""Tool for fetching files from GitHub."""

import os
import json
import time
from typing import List, Optional
from datetime import datetime
from fnmatch import fnmatch

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from github import Github, GithubException, RateLimitExceededException

from ..models.file_models import FetchedFile


class FetchGitHubFilesInput(BaseModel):
    """Input schema for FetchGitHubFilesTool."""

    repo_url: str = Field(description="GitHub repository URL (e.g., 'owner/repo' or full URL)")
    branch: str = Field(description="Branch name to fetch from")
    target_paths: List[str] = Field(description="List of glob patterns for files to fetch")
    auth_token: Optional[str] = Field(default=None, description="GitHub authentication token (optional)")


class FetchGitHubFilesTool(BaseTool):
    """Tool for fetching Markdown files from GitHub repository."""

    name: str = "fetch_github_files"
    description: str = """
    Fetches Markdown files from a GitHub repository.
    Input should be a JSON with: repo_url, branch, target_paths (list of glob patterns), auth_token (optional).
    Returns a list of fetched files with content and metadata.
    """
    args_schema: type[BaseModel] = FetchGitHubFilesInput

    def _run(
        self,
        repo_url: str,
        branch: str,
        target_paths: List[str],
        auth_token: Optional[str] = None
    ) -> str:
        """Execute the tool to fetch files from GitHub.
        
        Args:
            repo_url: GitHub repository URL or owner/repo format
            branch: Branch name to fetch from
            target_paths: List of glob patterns for files to fetch
            auth_token: Optional GitHub authentication token
            
        Returns:
            JSON string containing list of fetched files with metadata
        """
        # Get auth token from environment if not provided
        if auth_token is None:
            auth_token = os.environ.get("GITHUB_TOKEN")
        
        # Initialize GitHub client
        try:
            github_client = Github(auth_token) if auth_token else Github()
        except Exception as e:
            return json.dumps({
                "error": f"Failed to initialize GitHub client: {str(e)}",
                "files": []
            })
        
        # Parse repository URL to extract owner/repo
        repo_name = self._parse_repo_url(repo_url)
        if not repo_name:
            return json.dumps({
                "error": f"Invalid repository URL: {repo_url}",
                "files": []
            })
        
        # Fetch files with error handling and retry logic
        try:
            fetched_files = self._fetch_files_with_retry(
                github_client,
                repo_name,
                branch,
                target_paths,
                max_retries=3
            )
            
            # Convert to JSON-serializable format
            files_data = [
                {
                    "path": f.path,
                    "content": f.content,
                    "commit_hash": f.commit_hash,
                    "last_modified": f.last_modified.isoformat()
                }
                for f in fetched_files
            ]
            
            return json.dumps({
                "success": True,
                "files": files_data,
                "count": len(files_data)
            })
            
        except GithubException as e:
            error_msg = self._format_github_error(e)
            return json.dumps({
                "error": error_msg,
                "files": []
            })
        except Exception as e:
            return json.dumps({
                "error": f"Unexpected error: {str(e)}",
                "files": []
            })
        finally:
            github_client.close()

    def _parse_repo_url(self, repo_url: str) -> Optional[str]:
        """Parse repository URL to extract owner/repo format.
        
        Args:
            repo_url: GitHub repository URL or owner/repo format
            
        Returns:
            Repository in owner/repo format, or None if invalid
        """
        # If already in owner/repo format
        if "/" in repo_url and "github.com" not in repo_url:
            return repo_url
        
        # Parse from full URL
        if "github.com" in repo_url:
            parts = repo_url.rstrip("/").split("github.com/")
            if len(parts) == 2:
                repo_path = parts[1].replace(".git", "")
                return repo_path
        
        return None

    def _fetch_files_with_retry(
        self,
        github_client: Github,
        repo_name: str,
        branch: str,
        target_paths: List[str],
        max_retries: int = 3
    ) -> List[FetchedFile]:
        """Fetch files with exponential backoff retry logic.
        
        Args:
            github_client: Initialized GitHub client
            repo_name: Repository in owner/repo format
            branch: Branch name
            target_paths: List of glob patterns
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of fetched files
        """
        retry_count = 0
        backoff_time = 1  # Start with 1 second
        
        while retry_count <= max_retries:
            try:
                return self._fetch_files(github_client, repo_name, branch, target_paths)
            except RateLimitExceededException as e:
                if retry_count >= max_retries:
                    raise
                
                # Exponential backoff
                wait_time = backoff_time * (2 ** retry_count)
                time.sleep(wait_time)
                retry_count += 1
            except (ConnectionError, TimeoutError) as e:
                if retry_count >= max_retries:
                    raise GithubException(500, {"message": f"Network error after {max_retries} retries: {str(e)}"})
                
                # Exponential backoff for network errors
                wait_time = backoff_time * (2 ** retry_count)
                time.sleep(wait_time)
                retry_count += 1
        
        raise GithubException(500, {"message": f"Failed after {max_retries} retries"})

    def _fetch_files(
        self,
        github_client: Github,
        repo_name: str,
        branch: str,
        target_paths: List[str]
    ) -> List[FetchedFile]:
        """Fetch files matching glob patterns from repository.
        
        Args:
            github_client: Initialized GitHub client
            repo_name: Repository in owner/repo format
            branch: Branch name
            target_paths: List of glob patterns
            
        Returns:
            List of fetched files
        """
        # Get repository
        repo = github_client.get_repo(repo_name)
        
        # Get all files in repository recursively
        all_files = self._get_all_files_recursive(repo, branch, "")
        
        # Filter files matching glob patterns
        matching_files = []
        for file_path in all_files:
            if self._matches_any_pattern(file_path, target_paths):
                # Fetch file content and metadata
                try:
                    file_content = repo.get_contents(file_path, ref=branch)
                    
                    # Get commit information for this file
                    commits = repo.get_commits(path=file_path, sha=branch)
                    latest_commit = commits[0]
                    
                    # Decode content
                    content = file_content.decoded_content.decode('utf-8')
                    
                    fetched_file = FetchedFile(
                        path=file_path,
                        content=content,
                        commit_hash=latest_commit.sha,
                        last_modified=latest_commit.commit.author.date
                    )
                    matching_files.append(fetched_file)
                except Exception as e:
                    # Skip files that can't be fetched
                    continue
        
        return matching_files

    def _get_all_files_recursive(
        self,
        repo,
        branch: str,
        path: str
    ) -> List[str]:
        """Recursively get all file paths in repository.
        
        Args:
            repo: PyGithub repository object
            branch: Branch name
            path: Current path (empty string for root)
            
        Returns:
            List of all file paths
        """
        all_files = []
        
        try:
            contents = repo.get_contents(path, ref=branch)
            
            for content in contents:
                if content.type == "dir":
                    # Recursively get files from subdirectory
                    all_files.extend(self._get_all_files_recursive(repo, branch, content.path))
                else:
                    # Add file path
                    all_files.append(content.path)
        except Exception:
            # Skip directories that can't be accessed
            pass
        
        return all_files

    def _matches_any_pattern(self, file_path: str, patterns: List[str]) -> bool:
        """Check if file path matches any of the glob patterns.
        
        Args:
            file_path: File path to check
            patterns: List of glob patterns
            
        Returns:
            True if file matches any pattern
        """
        for pattern in patterns:
            if fnmatch(file_path, pattern):
                return True
        return False

    def _format_github_error(self, error: GithubException) -> str:
        """Format GitHub API error into user-friendly message.
        
        Args:
            error: GitHub exception
            
        Returns:
            Formatted error message
        """
        if error.status == 401:
            return "Authentication failed. Please provide a valid GITHUB_TOKEN."
        elif error.status == 404:
            return "Repository not found. Please check the repository URL and branch name."
        elif error.status == 403:
            return "Rate limit exceeded. Please wait before retrying or provide authentication token."
        else:
            return f"GitHub API error ({error.status}): {error.data.get('message', str(error))}"

    async def _arun(self, *args, **kwargs) -> str:
        """Async execution (not implemented)."""
        raise NotImplementedError("Async execution not supported")
