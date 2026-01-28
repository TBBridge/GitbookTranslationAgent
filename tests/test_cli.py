"""Tests for CLI interface."""

import argparse
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.cli import parse_args, validate_config, main
from src.models.config import CLIConfig


class TestParseArgs:
    """Test CLI argument parsing."""

    def test_parse_args_minimal(self):
        """Test parsing minimal required arguments."""
        test_args = [
            "--repo-url", "https://github.com/test/repo",
            "--target-paths", "*.md",
            "--languages", "en",
            "--glossary-path", "glossary.json"
        ]
        
        with patch('sys.argv', ['gitbook-translator'] + test_args):
            args = parse_args()
            
        assert args.repo_url == "https://github.com/test/repo"
        assert args.branch == "main"  # default
        assert args.target_paths == ["*.md"]
        assert args.languages == ["en"]
        assert args.glossary_path == "glossary.json"
        assert args.output_root == "./output"  # default
        assert args.push_option == "none"  # default
        assert args.output_naming == "suffix"  # default

    def test_parse_args_all_options(self):
        """Test parsing all available arguments."""
        test_args = [
            "--repo-url", "https://github.com/test/repo",
            "--branch", "develop",
            "--target-paths", "docs/**/*.md", "README.md",
            "--languages", "en", "zh-CN", "zh-TW",
            "--glossary-path", "terms.json",
            "--output-root", "./translations",
            "--push-option", "push_same_repo_new_branch",
            "--output-naming", "directory"
        ]
        
        with patch('sys.argv', ['gitbook-translator'] + test_args):
            args = parse_args()
            
        assert args.repo_url == "https://github.com/test/repo"
        assert args.branch == "develop"
        assert args.target_paths == ["docs/**/*.md", "README.md"]
        assert args.languages == ["en", "zh-CN", "zh-TW"]
        assert args.glossary_path == "terms.json"
        assert args.output_root == "./translations"
        assert args.push_option == "push_same_repo_new_branch"
        assert args.output_naming == "directory"

    def test_parse_args_missing_required(self):
        """Test error when required arguments are missing."""
        test_args = ["--repo-url", "https://github.com/test/repo"]
        
        with patch('sys.argv', ['gitbook-translator'] + test_args):
            with pytest.raises(SystemExit):
                parse_args()


class TestValidateConfig:
    """Test configuration validation."""

    def test_validate_config_success(self):
        """Test successful configuration validation."""
        # Create temporary glossary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            # Create temporary output directory
            with tempfile.TemporaryDirectory() as output_dir:
                args = argparse.Namespace(
                    repo_url="https://github.com/test/repo",
                    branch="main",
                    target_paths=["*.md"],
                    languages=["en"],
                    glossary_path=glossary_path,
                    output_root=output_dir,
                    push_option="none",
                    output_naming="suffix"
                )
                
                config = validate_config(args)
                
                assert isinstance(config, CLIConfig)
                assert config.repo_url == "https://github.com/test/repo"
                assert config.branch == "main"
                assert config.target_paths == ["*.md"]
                assert config.languages == ["en"]
                assert config.glossary_path == glossary_path
                assert config.output_root == output_dir
                assert config.push_option == "none"
                assert config.output_naming == "suffix"
        finally:
            # Clean up
            os.unlink(glossary_path)

    def test_validate_config_invalid_repo_url(self):
        """Test validation error for invalid repository URL."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                args = argparse.Namespace(
                    repo_url="invalid-url",
                    branch="main",
                    target_paths=["*.md"],
                    languages=["en"],
                    glossary_path=glossary_path,
                    output_root=output_dir,
                    push_option="none",
                    output_naming="suffix"
                )
                
                with pytest.raises(ValueError, match="Only GitHub URLs are supported"):
                    validate_config(args)
        finally:
            os.unlink(glossary_path)

    def test_validate_config_non_github_url(self):
        """Test validation error for non-GitHub URL."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                args = argparse.Namespace(
                    repo_url="https://gitlab.com/test/repo",
                    branch="main",
                    target_paths=["*.md"],
                    languages=["en"],
                    glossary_path=glossary_path,
                    output_root=output_dir,
                    push_option="none",
                    output_naming="suffix"
                )
                
                with pytest.raises(ValueError, match="Only GitHub URLs are supported"):
                    validate_config(args)
        finally:
            os.unlink(glossary_path)

    def test_validate_config_empty_branch(self):
        """Test validation error for empty branch name."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                args = argparse.Namespace(
                    repo_url="https://github.com/test/repo",
                    branch="",
                    target_paths=["*.md"],
                    languages=["en"],
                    glossary_path=glossary_path,
                    output_root=output_dir,
                    push_option="none",
                    output_naming="suffix"
                )
                
                with pytest.raises(ValueError, match="branch must be non-empty"):
                    validate_config(args)
        finally:
            os.unlink(glossary_path)

    def test_validate_config_invalid_branch_name(self):
        """Test validation error for invalid branch name."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                args = argparse.Namespace(
                    repo_url="https://github.com/test/repo",
                    branch="invalid branch name",
                    target_paths=["*.md"],
                    languages=["en"],
                    glossary_path=glossary_path,
                    output_root=output_dir,
                    push_option="none",
                    output_naming="suffix"
                )
                
                with pytest.raises(ValueError, match="Invalid branch name format"):
                    validate_config(args)
        finally:
            os.unlink(glossary_path)

    def test_validate_config_empty_target_paths(self):
        """Test validation error for empty target paths."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                args = argparse.Namespace(
                    repo_url="https://github.com/test/repo",
                    branch="main",
                    target_paths=[],
                    languages=["en"],
                    glossary_path=glossary_path,
                    output_root=output_dir,
                    push_option="none",
                    output_naming="suffix"
                )
                
                with pytest.raises(ValueError, match="target_paths must contain at least one pattern"):
                    validate_config(args)
        finally:
            os.unlink(glossary_path)

    def test_validate_config_empty_languages(self):
        """Test validation error for empty languages."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                args = argparse.Namespace(
                    repo_url="https://github.com/test/repo",
                    branch="main",
                    target_paths=["*.md"],
                    languages=[],
                    glossary_path=glossary_path,
                    output_root=output_dir,
                    push_option="none",
                    output_naming="suffix"
                )
                
                with pytest.raises(ValueError, match="languages must contain at least one language code"):
                    validate_config(args)
        finally:
            os.unlink(glossary_path)

    def test_validate_config_invalid_language_code(self):
        """Test validation error for invalid language code."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                args = argparse.Namespace(
                    repo_url="https://github.com/test/repo",
                    branch="main",
                    target_paths=["*.md"],
                    languages=["invalid-lang-code"],
                    glossary_path=glossary_path,
                    output_root=output_dir,
                    push_option="none",
                    output_naming="suffix"
                )
                
                with pytest.raises(ValueError, match="Invalid language code format"):
                    validate_config(args)
        finally:
            os.unlink(glossary_path)

    def test_validate_config_missing_glossary_file(self):
        """Test validation error for missing glossary file."""
        with tempfile.TemporaryDirectory() as output_dir:
            args = argparse.Namespace(
                repo_url="https://github.com/test/repo",
                branch="main",
                target_paths=["*.md"],
                languages=["en"],
                glossary_path="/nonexistent/glossary.json",
                output_root=output_dir,
                push_option="none",
                output_naming="suffix"
            )
            
            with pytest.raises(ValueError, match="Glossary file not found"):
                validate_config(args)

    def test_validate_config_invalid_glossary_extension(self):
        """Test validation error for invalid glossary file extension."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('some content')
            glossary_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as output_dir:
                args = argparse.Namespace(
                    repo_url="https://github.com/test/repo",
                    branch="main",
                    target_paths=["*.md"],
                    languages=["en"],
                    glossary_path=glossary_path,
                    output_root=output_dir,
                    push_option="none",
                    output_naming="suffix"
                )
                
                with pytest.raises(ValueError, match="Glossary file must be JSON or CSV"):
                    validate_config(args)
        finally:
            os.unlink(glossary_path)


class TestMainFunction:
    """Test main CLI entry point."""

    @patch('src.agent.TranslationAgent')
    @patch('src.cli.load_dotenv')
    @patch('os.getenv')
    @patch('sys.argv')
    def test_main_success(self, mock_argv, mock_getenv, mock_load_dotenv, mock_agent_class):
        """Test successful main execution."""
        # Create temporary glossary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            # Mock command line arguments
            mock_argv.__getitem__.side_effect = lambda x: [
                'gitbook-translator',
                '--repo-url', 'https://github.com/test/repo',
                '--target-paths', '*.md',
                '--languages', 'en',
                '--glossary-path', glossary_path
            ][x]
            mock_argv.__len__.return_value = 6
            
            # Mock environment variables
            mock_getenv.side_effect = lambda key, default=None: {
                'OPENAI_API_KEY': 'test-key'
            }.get(key, default)
            
            # Mock agent
            mock_agent = MagicMock()
            mock_agent.run.return_value = "Translation completed"
            mock_agent_class.return_value = mock_agent
            
            # Run main
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            # Should exit with code 0 (success)
            assert exc_info.value.code == 0
            
            # Verify agent was created and run
            mock_agent_class.assert_called_once()
            mock_agent.run.assert_called_once()
            
        finally:
            os.unlink(glossary_path)

    @patch('sys.argv')
    def test_main_missing_required_args(self, mock_argv):
        """Test main with missing required arguments."""
        # Mock incomplete command line arguments
        mock_argv.__getitem__.side_effect = lambda x: [
            'gitbook-translator',
            '--repo-url', 'https://github.com/test/repo'
        ][x]
        mock_argv.__len__.return_value = 3
        
        # Should exit with error code
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code != 0

    @patch('os.getenv')
    @patch('sys.argv')
    def test_main_missing_api_key(self, mock_argv, mock_getenv):
        """Test main with missing API key."""
        # Create temporary glossary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            # Mock command line arguments
            mock_argv.__getitem__.side_effect = lambda x: [
                'gitbook-translator',
                '--repo-url', 'https://github.com/test/repo',
                '--target-paths', '*.md',
                '--languages', 'en',
                '--glossary-path', glossary_path
            ][x]
            mock_argv.__len__.return_value = 6
            
            # Mock missing environment variables
            mock_getenv.return_value = None
            
            # Should exit with error code 1
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
            
        finally:
            os.unlink(glossary_path)

    @patch('src.agent.TranslationAgent')
    @patch('src.cli.load_dotenv')
    @patch('os.getenv')
    @patch('sys.argv')
    def test_main_keyboard_interrupt(self, mock_argv, mock_getenv, mock_load_dotenv, mock_agent_class):
        """Test main with keyboard interrupt."""
        # Create temporary glossary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            # Mock command line arguments
            mock_argv.__getitem__.side_effect = lambda x: [
                'gitbook-translator',
                '--repo-url', 'https://github.com/test/repo',
                '--target-paths', '*.md',
                '--languages', 'en',
                '--glossary-path', glossary_path
            ][x]
            mock_argv.__len__.return_value = 6
            
            # Mock environment variables
            mock_getenv.side_effect = lambda key, default=None: {
                'OPENAI_API_KEY': 'test-key'
            }.get(key, default)
            
            # Mock agent to raise KeyboardInterrupt
            mock_agent = MagicMock()
            mock_agent.run.side_effect = KeyboardInterrupt()
            mock_agent_class.return_value = mock_agent
            
            # Should exit with code 130 (SIGINT)
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 130
            
        finally:
            os.unlink(glossary_path)

    @patch('src.agent.TranslationAgent')
    @patch('src.cli.load_dotenv')
    @patch('os.getenv')
    @patch('sys.argv')
    def test_main_file_not_found_error(self, mock_argv, mock_getenv, mock_load_dotenv, mock_agent_class):
        """Test main with FileNotFoundError."""
        # Create temporary glossary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            # Mock command line arguments
            mock_argv.__getitem__.side_effect = lambda x: [
                'gitbook-translator',
                '--repo-url', 'https://github.com/test/repo',
                '--target-paths', '*.md',
                '--languages', 'en',
                '--glossary-path', glossary_path
            ][x]
            mock_argv.__len__.return_value = 6
            
            # Mock environment variables
            mock_getenv.side_effect = lambda key, default=None: {
                'OPENAI_API_KEY': 'test-key'
            }.get(key, default)
            
            # Mock agent to raise FileNotFoundError
            mock_agent = MagicMock()
            mock_agent.run.side_effect = FileNotFoundError("File not found")
            mock_agent_class.return_value = mock_agent
            
            # Should exit with code 2
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 2
            
        finally:
            os.unlink(glossary_path)

    @patch('src.agent.TranslationAgent')
    @patch('src.cli.load_dotenv')
    @patch('os.getenv')
    @patch('sys.argv')
    def test_main_permission_error(self, mock_argv, mock_getenv, mock_load_dotenv, mock_agent_class):
        """Test main with PermissionError."""
        # Create temporary glossary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            # Mock command line arguments
            mock_argv.__getitem__.side_effect = lambda x: [
                'gitbook-translator',
                '--repo-url', 'https://github.com/test/repo',
                '--target-paths', '*.md',
                '--languages', 'en',
                '--glossary-path', glossary_path
            ][x]
            mock_argv.__len__.return_value = 6
            
            # Mock environment variables
            mock_getenv.side_effect = lambda key, default=None: {
                'OPENAI_API_KEY': 'test-key'
            }.get(key, default)
            
            # Mock agent to raise PermissionError
            mock_agent = MagicMock()
            mock_agent.run.side_effect = PermissionError("Permission denied")
            mock_agent_class.return_value = mock_agent
            
            # Should exit with code 13
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 13
            
        finally:
            os.unlink(glossary_path)

    @patch('src.agent.TranslationAgent')
    @patch('src.cli.load_dotenv')
    @patch('os.getenv')
    @patch('sys.argv')
    def test_main_unexpected_error(self, mock_argv, mock_getenv, mock_load_dotenv, mock_agent_class):
        """Test main with unexpected error."""
        # Create temporary glossary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"terms": []}')
            glossary_path = f.name
        
        try:
            # Mock command line arguments
            mock_argv.__getitem__.side_effect = lambda x: [
                'gitbook-translator',
                '--repo-url', 'https://github.com/test/repo',
                '--target-paths', '*.md',
                '--languages', 'en',
                '--glossary-path', glossary_path
            ][x]
            mock_argv.__len__.return_value = 6
            
            # Mock environment variables
            mock_getenv.side_effect = lambda key, default=None: {
                'OPENAI_API_KEY': 'test-key'
            }.get(key, default)
            
            # Mock agent to raise unexpected error
            mock_agent = MagicMock()
            mock_agent.run.side_effect = RuntimeError("Unexpected error")
            mock_agent_class.return_value = mock_agent
            
            # Should exit with code 1
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
            
        finally:
            os.unlink(glossary_path)