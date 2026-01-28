"""Command-line interface for GitBook Translator."""

import argparse
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from .models import CLIConfig


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="GitBook Translator - AI Agent-based documentation translator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate to English and Chinese
  %(prog)s --repo-url https://github.com/user/docs \\
           --target-paths "docs/**/*.md" "README.md" \\
           --languages en zh-CN \\
           --glossary-path glossary.json

  # Translate with directory naming and GitHub push
  %(prog)s --repo-url https://github.com/user/docs \\
           --branch develop \\
           --target-paths "**/*.md" \\
           --languages en zh-CN zh-TW \\
           --glossary-path terms.json \\
           --output-root ./translations \\
           --output-naming directory \\
           --push-option push_same_repo_new_branch

Environment Variables:
  GITHUB_TOKEN    GitHub personal access token for private repositories
  OPENAI_API_KEY  OpenAI API key for translation (required)
  ANTHROPIC_API_KEY  Alternative to OpenAI (optional)
        """,
    )

    parser.add_argument(
        "--repo-url",
        required=True,
        metavar="URL",
        help="GitHub repository URL (e.g., https://github.com/user/repo)",
    )

    parser.add_argument(
        "--branch",
        default="main",
        metavar="NAME",
        help="Branch name to fetch files from (default: %(default)s)",
    )

    parser.add_argument(
        "--target-paths",
        nargs="+",
        required=True,
        metavar="PATTERN",
        help="Glob patterns for target files. Examples: 'docs/**/*.md', 'README.md', '**/*.md'",
    )

    parser.add_argument(
        "--languages",
        nargs="+",
        required=True,
        metavar="LANG",
        help="Target languages for translation. Examples: 'en', 'zh-CN', 'zh-TW', 'ko', 'fr'",
    )

    parser.add_argument(
        "--glossary-path",
        required=True,
        metavar="PATH",
        help="Path to glossary JSON file containing technical term translations",
    )

    parser.add_argument(
        "--output-root",
        default="./output",
        metavar="DIR",
        help="Output directory for translated files (default: %(default)s)",
    )

    parser.add_argument(
        "--push-option",
        choices=["none", "push_same_repo_direct", "push_same_repo_new_branch"],
        default="none",
        metavar="OPTION",
        help="GitHub push strategy: 'none' (local only), 'push_same_repo_direct' (push to same branch), 'push_same_repo_new_branch' (create new branch) (default: %(default)s)",
    )

    parser.add_argument(
        "--output-naming",
        choices=["suffix", "directory"],
        default="suffix",
        metavar="MODE",
        help="File naming convention: 'suffix' (file.en.md), 'directory' (/en/file.md) (default: %(default)s)",
    )

    return parser.parse_args()


def validate_config(args: argparse.Namespace) -> CLIConfig:
    """Validate configuration and create CLIConfig.

    Args:
        args: Parsed command-line arguments

    Returns:
        Validated CLIConfig instance

    Raises:
        ValueError: If validation fails
    """
    # Create and validate config (validation happens in __post_init__)
    config = CLIConfig(
        repo_url=args.repo_url,
        branch=args.branch,
        target_paths=args.target_paths,
        languages=args.languages,
        glossary_path=args.glossary_path,
        output_root=args.output_root,
        push_option=args.push_option,
        output_naming=args.output_naming,
    )

    return config


def main():
    """Main entry point for CLI."""
    # Load environment variables
    load_dotenv()

    try:
        # Parse and validate arguments
        args = parse_args()
        config = validate_config(args)

        # Check for required environment variables
        import os
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            print("Error: Either OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable must be set", file=sys.stderr)
            sys.exit(1)

        # Initialize and run agent
        print(f"Starting GitBook Translator...")
        print(f"Repository: {config.repo_url}")
        print(f"Branch: {config.branch}")
        print(f"Target paths: {', '.join(config.target_paths)}")
        print(f"Languages: {', '.join(config.languages)}")
        print(f"Output: {config.output_root} ({config.output_naming} naming)")
        print(f"Push option: {config.push_option}")
        print()

        # Import TranslationAgent only when needed
        from .agent import TranslationAgent
        agent = TranslationAgent(config)
        result = agent.run()

        # Print results
        print(f"\nTranslation completed successfully!")
        print(f"Result: {result}")
        sys.exit(0)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)  # Standard exit code for SIGINT
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"File not found: {e}", file=sys.stderr)
        sys.exit(2)
    except PermissionError as e:
        print(f"Permission denied: {e}", file=sys.stderr)
        sys.exit(13)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
