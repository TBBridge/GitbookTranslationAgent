"""Tool for pushing translations to GitHub."""

import os
import json
from typing import List, Dict, Literal, Optional
from datetime import datetime

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from github import Github, GithubException


class FileContent(BaseModel):
    """Represents a file to be pushed to GitHub."""
    
    path: str = Field(description="File path in repository")
    content: str = Field(description="File content")


class PushToGitHubInput(BaseModel):
    """Input schema for PushToGitHubTool."""

    repo_url: str = Field(description="GitHub repository URL (e.g., 'owner/repo' or full URL)")
    branch: str = Field(description="Source branch name")
    files: List[Dict[str, str]] = Field(description="List of files with 'path' and 'content' keys")
    push_option: Literal["push_same_repo_direct", "push_same_repo_new_branch"] = Field(
        description="Push option: 'push_same_repo_direct' or 'push_same_repo_new_branch'"
    )
    language: str = Field(description="Target language code for branch naming")
    auth_token: Optional[str] = Field(default=None, description="GitHub authentication token")
    user_confirmation: bool = Field(
        default=False,
        description="User confirmation for direct push (required for push_same_repo_direct)"
    )


class PushToGitHubTool(BaseTool):
    """Tool for pushing translated files to GitHub repository."""

    name: str = "push_to_github"
    description: str = """
    Pushes translated files to GitHub repository.
    Input should be a JSON with: repo_url (string), branch (string), files (list of dicts with 'path' and 'content'), 
    push_option (string), language (string), auth_token (optional string), user_confirmation (optional boolean).
    Returns push result with success status, branch name, and PR information.
    """
    args_schema: type[BaseModel] = PushToGitHubInput

    def _run(
        self,
        repo_url: str,
        branch: str,
        files: List[Dict[str, str]],
        push_option: Literal["push_same_repo_direct", "push_same_repo_new_branch"],
        language: str,
        auth_token: Optional[str] = None,
        user_confirmation: bool = False
    ) -> str:
        """Execute the tool to push files to GitHub.
        
        Args:
            repo_url: GitHub repository URL or owner/repo format
            branch: Source branch name
            files: List of dicts with 'path' and 'content' keys
            push_option: 'push_same_repo_direct' or 'push_same_repo_new_branch'
            language: Target language code for branch naming
            auth_token: Optional GitHub authentication token
            user_confirmation: User confirmation for direct push
            
        Returns:
            JSON string containing push result with branch name and PR information
        """
        # Get auth token from environment if not provided
        if auth_token is None:
            auth_token = os.environ.get("GITHUB_TOKEN")
        
        if not auth_token:
            return json.dumps({
                "success": False,
                "error": "GitHub authentication token is required for push operations. Please set GITHUB_TOKEN environment variable.",
                "branch_name": None,
                "pr_url": None
            })
        
        # Initialize GitHub client
        try:
            github_client = Github(auth_token)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Failed to initialize GitHub client: {str(e)}",
                "branch_name": None,
                "pr_url": None
            })
        
        try:
            # Parse repository URL
            repo_name = self._parse_repo_url(repo_url)
            if not repo_name:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid repository URL: {repo_url}",
                    "branch_name": None,
                    "pr_url": None
                })
            
            # Get repository
            repo = github_client.get_repo(repo_name)
            
            # Handle different push options
            if push_option == "push_same_repo_direct":
                result = self._push_direct(
                    repo=repo,
                    branch=branch,
                    files=files,
                    user_confirmation=user_confirmation
                )
            else:  # push_same_repo_new_branch
                result = self._push_new_branch(
                    repo=repo,
                    source_branch=branch,
                    files=files,
                    language=language
                )
            
            return json.dumps(result)
            
        except GithubException as e:
            error_msg = self._format_github_error(e)
            return json.dumps({
                "success": False,
                "error": error_msg,
                "branch_name": None,
                "pr_url": None
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "branch_name": None,
                "pr_url": None
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

    def _push_direct(
        self,
        repo,
        branch: str,
        files: List[Dict[str, str]],
        user_confirmation: bool
    ) -> Dict:
        """Push files directly to the same branch.
        
        Args:
            repo: PyGithub repository object
            branch: Branch name to push to
            files: List of files to push
            user_confirmation: Whether user has confirmed the push
            
        Returns:
            Result dictionary
        """
        if not user_confirmation:
            return {
                "success": False,
                "error": "Direct push to same branch requires explicit user confirmation. Set user_confirmation=True to proceed.",
                "branch_name": branch,
                "pr_url": None,
                "requires_confirmation": True
            }
        
        try:
            # Push each file to the branch
            for file_data in files:
                file_path = file_data["path"]
                file_content = file_data["content"]
                
                try:
                    # Check if file exists
                    existing_file = repo.get_contents(file_path, ref=branch)
                    
                    # Update existing file
                    repo.update_file(
                        path=file_path,
                        message=f"Update translation: {file_path}",
                        content=file_content,
                        sha=existing_file.sha,
                        branch=branch
                    )
                except GithubException as e:
                    if e.status == 404:
                        # File doesn't exist, create it
                        repo.create_file(
                            path=file_path,
                            message=f"Add translation: {file_path}",
                            content=file_content,
                            branch=branch
                        )
                    else:
                        raise
            
            return {
                "success": True,
                "branch_name": branch,
                "pr_url": None,
                "message": f"Successfully pushed {len(files)} file(s) to branch '{branch}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to push files: {str(e)}",
                "branch_name": branch,
                "pr_url": None
            }

    def _push_new_branch(
        self,
        repo,
        source_branch: str,
        files: List[Dict[str, str]],
        language: str
    ) -> Dict:
        """Create a new branch and push files to it.
        
        Args:
            repo: PyGithub repository object
            source_branch: Source branch to branch from
            files: List of files to push
            language: Target language code
            
        Returns:
            Result dictionary with branch name and PR information
        """
        try:
            # Generate new branch name
            new_branch_name = self._generate_branch_name(language)
            
            # Get source branch reference
            source_ref = repo.get_git_ref(f"heads/{source_branch}")
            source_sha = source_ref.object.sha
            
            # Create new branch
            try:
                repo.create_git_ref(
                    ref=f"refs/heads/{new_branch_name}",
                    sha=source_sha
                )
            except GithubException as e:
                if e.status == 422:
                    # Branch already exists, use it
                    pass
                else:
                    raise
            
            # Push each file to the new branch
            for file_data in files:
                file_path = file_data["path"]
                file_content = file_data["content"]
                
                try:
                    # Check if file exists
                    existing_file = repo.get_contents(file_path, ref=new_branch_name)
                    
                    # Update existing file
                    repo.update_file(
                        path=file_path,
                        message=f"Update translation: {file_path}",
                        content=file_content,
                        sha=existing_file.sha,
                        branch=new_branch_name
                    )
                except GithubException as e:
                    if e.status == 404:
                        # File doesn't exist, create it
                        repo.create_file(
                            path=file_path,
                            message=f"Add translation: {file_path}",
                            content=file_content,
                            branch=new_branch_name
                        )
                    else:
                        raise
            
            # Generate PR information
            pr_info = self._generate_pr_info(
                repo=repo,
                source_branch=source_branch,
                new_branch=new_branch_name,
                language=language,
                file_count=len(files)
            )
            
            return {
                "success": True,
                "branch_name": new_branch_name,
                "pr_url": None,
                "pr_info": pr_info,
                "message": f"Successfully pushed {len(files)} file(s) to new branch '{new_branch_name}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create branch and push files: {str(e)}",
                "branch_name": None,
                "pr_url": None
            }

    def _generate_branch_name(self, language: str) -> str:
        """Generate branch name for translation.
        
        Args:
            language: Target language code
            
        Returns:
            Branch name in format: translation/<lang>/<timestamp>
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"translation/{language}/{timestamp}"

    def _generate_pr_info(
        self,
        repo,
        source_branch: str,
        new_branch: str,
        language: str,
        file_count: int
    ) -> Dict[str, str]:
        """Generate pull request information.
        
        Args:
            repo: PyGithub repository object
            source_branch: Source branch name
            new_branch: New branch name
            language: Target language code
            file_count: Number of files translated
            
        Returns:
            Dictionary with PR creation instructions
        """
        repo_full_name = repo.full_name
        
        pr_title = f"Add {language} translations ({file_count} files)"
        pr_body = f"""This PR adds translations to {language}.

**Summary:**
- {file_count} file(s) translated
- Target language: {language}
- Source branch: {source_branch}

**To create this PR:**
1. Go to: https://github.com/{repo_full_name}/compare/{source_branch}...{new_branch}
2. Click "Create pull request"
3. Review the changes and merge when ready
"""
        
        return {
            "branch_name": new_branch,
            "source_branch": source_branch,
            "pr_title": pr_title,
            "pr_body": pr_body,
            "pr_url": f"https://github.com/{repo_full_name}/compare/{source_branch}...{new_branch}",
            "instructions": f"To create a pull request, visit: https://github.com/{repo_full_name}/compare/{source_branch}...{new_branch}"
        }

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
            return "Repository or branch not found. Please check the repository URL and branch name."
        elif error.status == 403:
            return "Permission denied. Please ensure your token has write access to the repository."
        elif error.status == 422:
            return f"Validation error: {error.data.get('message', str(error))}"
        else:
            return f"GitHub API error ({error.status}): {error.data.get('message', str(error))}"

    async def _arun(self, *args, **kwargs) -> str:
        """Async execution (not implemented)."""
        raise NotImplementedError("Async execution not supported")
