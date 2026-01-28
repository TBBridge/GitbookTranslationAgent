"""Configuration models for GitBook Translator."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal
from urllib.parse import urlparse


@dataclass
class CLIConfig:
    """CLI configuration parameters."""

    repo_url: str
    branch: str
    target_paths: List[str]
    languages: List[str]
    glossary_path: str
    output_root: str
    push_option: Literal["none", "push_same_repo_direct", "push_same_repo_new_branch"] = "none"
    output_naming: Literal["suffix", "directory"] = "suffix"

    def __post_init__(self):
        """Validate configuration parameters."""
        self._validate_repo_url()
        self._validate_branch()
        self._validate_target_paths()
        self._validate_languages()
        self._validate_glossary_path()
        self._validate_output_root()

    def _validate_repo_url(self):
        """Validate GitHub repository URL format."""
        if not self.repo_url:
            raise ValueError("repo_url must be non-empty")
        
        # Parse URL
        try:
            parsed = urlparse(self.repo_url)
        except Exception:
            raise ValueError(f"Invalid URL format: {self.repo_url}")
        
        # Check if it's a GitHub URL
        if parsed.netloc not in ["github.com", "www.github.com"]:
            raise ValueError(f"Only GitHub URLs are supported: {self.repo_url}")
        
        # Check path format (should be /owner/repo or /owner/repo.git)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2:
            raise ValueError(f"Invalid GitHub repository path: {self.repo_url}")
        
        # Remove .git suffix if present
        if path_parts[-1].endswith(".git"):
            path_parts[-1] = path_parts[-1][:-4]
        
        if not path_parts[0] or not path_parts[1]:
            raise ValueError(f"Invalid GitHub repository path: {self.repo_url}")

    def _validate_branch(self):
        """Validate branch name."""
        if not self.branch:
            raise ValueError("branch must be non-empty")
        
        # Basic branch name validation (no spaces, no special chars except - and _)
        if not re.match(r"^[a-zA-Z0-9._/-]+$", self.branch):
            raise ValueError(f"Invalid branch name format: {self.branch}")

    def _validate_target_paths(self):
        """Validate target path patterns."""
        if not self.target_paths:
            raise ValueError("target_paths must contain at least one pattern")
        
        for pattern in self.target_paths:
            if not pattern or not pattern.strip():
                raise ValueError("target_paths cannot contain empty patterns")

    def _validate_languages(self):
        """Validate language codes."""
        if not self.languages:
            raise ValueError("languages must contain at least one language code")
        
        # Common language codes validation
        valid_languages = {
            "en", "zh-CN", "zh-TW", "ja", "ko", "fr", "de", "es", "it", "pt", "ru",
            "ar", "hi", "th", "vi", "id", "ms", "tl", "nl", "sv", "da", "no", "fi",
            "pl", "cs", "sk", "hu", "ro", "bg", "hr", "sr", "sl", "et", "lv", "lt",
            "uk", "be", "mk", "sq", "mt", "is", "ga", "cy", "eu", "ca", "gl", "pt-BR"
        }
        
        for lang in self.languages:
            if not lang or not lang.strip():
                raise ValueError("languages cannot contain empty language codes")
            if lang not in valid_languages:
                # Allow custom language codes but warn
                if not re.match(r"^[a-z]{2}(-[A-Z]{2})?$", lang):
                    raise ValueError(f"Invalid language code format: {lang}")

    def _validate_glossary_path(self):
        """Validate glossary file path."""
        if not self.glossary_path:
            raise ValueError("glossary_path must be non-empty")
        
        # Check if file exists
        glossary_file = Path(self.glossary_path)
        if not glossary_file.exists():
            raise ValueError(f"Glossary file not found: {self.glossary_path}")
        
        # Check if it's a file (not directory)
        if not glossary_file.is_file():
            raise ValueError(f"Glossary path must be a file: {self.glossary_path}")
        
        # Check file extension
        if glossary_file.suffix.lower() not in [".json", ".csv"]:
            raise ValueError(f"Glossary file must be JSON or CSV: {self.glossary_path}")

    def _validate_output_root(self):
        """Validate output root path."""
        if not self.output_root:
            raise ValueError("output_root must be non-empty")
        
        # Try to create the directory if it doesn't exist
        try:
            output_path = Path(self.output_root)
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Cannot create output directory {self.output_root}: {e}")
        
        # Check if it's writable
        if not output_path.is_dir():
            raise ValueError(f"Output root must be a directory: {self.output_root}")
