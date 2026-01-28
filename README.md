# GitBook Translator

AI Agent-based GitBook documentation translator that preserves all GitBook-specific syntax, structure, and formatting while translating Japanese content to multiple target languages.

## Overview

GitBook Translator uses a LangChain ReAct Agent with 10 specialized tools to autonomously translate GitBook-formatted Markdown documentation from Japanese to multiple target languages. The system maintains complete format preservation while ensuring translation quality through an AI-powered review process.

**Key Capabilities:**
- Autonomous translation workflow orchestrated by LangChain ReAct Agent
- Perfect format preservation of GitBook syntax, code blocks, links, and structure
- Diff detection to process only changed files and minimize LLM token consumption
- Iterative quality review with automatic correction (up to 2 iterations)
- Multi-language support in a single run
- Glossary-based terminology consistency
- Optional GitHub integration for fetching and pushing translations

## Features

- **Autonomous Translation Workflow**: LangChain Agent orchestrates the entire translation process using 10 custom tools
- **Format Preservation**: Maintains all GitBook syntax, code blocks, links, tables, and structure exactly as in the original
- **Protected Regions**: Automatically detects and preserves code blocks, inline code, URLs, YAML frontmatter, GitBook tags, and HTML
- **Diff Detection**: Processes only changed files to minimize LLM token consumption and API costs
- **Quality Review**: Separate AI reviewer validates translations and classifies issues by severity (BLOCKER, MAJOR, MINOR)
- **Iterative Correction**: Automatically corrects critical issues up to 2 times before finalizing
- **Multi-language Support**: Translate to multiple languages in a single run
- **Glossary Support**: Apply consistent terminology across all translations
- **GitHub Integration**: Fetch from GitHub repositories and optionally push translations back
- **Comprehensive Logging**: Track progress, errors, and issues at every stage
- **Error Isolation**: Errors in one file or language don't prevent processing of others

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- GitHub account (for accessing repositories)
- OpenAI API key or Anthropic API key (for translation)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd gitbook-translator

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file with your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
# GitHub Configuration
GITHUB_TOKEN=your_github_token_here

# LLM Configuration
# OpenAI (used for translation)
OPENAI_API_KEY=your_openai_api_key_here

# Google Gemini (used for review)
GOOGLE_API_KEY=your_google_api_key_here

# Optional: LangChain Tracing
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your_langchain_api_key_here
LANGCHAIN_PROJECT=gitbook-translator

# Agent Configuration
MAX_ITERATIONS=50
MAX_CORRECTION_LOOPS=2
TRANSLATION_TIMEOUT=300
```

### Configuration Details

- **GITHUB_TOKEN**: Required for accessing private repositories. Create a personal access token at https://github.com/settings/tokens with `repo` scope
- **OPENAI_API_KEY**: Required for translation. Get it from https://platform.openai.com/api-keys
- **GOOGLE_API_KEY**: Required for review. Get it from https://console.cloud.google.com/apis/credentials
- **LANGCHAIN_TRACING_V2**: Enable LangChain tracing for debugging (set to `true` for development)
- **MAX_ITERATIONS**: Maximum number of agent actions (default: 50)
- **MAX_CORRECTION_LOOPS**: Maximum correction iterations per file (default: 2)
- **TRANSLATION_TIMEOUT**: Timeout in seconds for each file translation (default: 300)

## Usage

### Basic Usage

Translate a repository to English:

```bash
python -m src.cli \
  --repo-url https://github.com/user/repo \
  --branch main \
  --target-paths "docs/**/*.md" "README.md" \
  --languages en \
  --glossary-path ./glossary.json \
  --output-root ./output
```

### Multiple Languages

Translate to multiple languages in one run:

```bash
python -m src.cli \
  --repo-url https://github.com/user/repo \
  --branch main \
  --target-paths "docs/**/*.md" \
  --languages en zh-CN zh-TW ko \
  --glossary-path ./glossary.json \
  --output-root ./output
```

### With Directory Naming

Use directory-based naming convention (`/en/file.md` instead of `file.en.md`):

```bash
python -m src.cli \
  --repo-url https://github.com/user/repo \
  --branch main \
  --target-paths "docs/**/*.md" \
  --languages en zh-CN \
  --glossary-path ./glossary.json \
  --output-root ./output \
  --output-naming directory
```

### With GitHub Push

Create a new branch and push translations to GitHub:

```bash
python -m src.cli \
  --repo-url https://github.com/user/repo \
  --branch main \
  --target-paths "docs/**/*.md" \
  --languages en \
  --glossary-path ./glossary.json \
  --output-root ./output \
  --push-option push_same_repo_new_branch
```

### CLI Parameters

```
--repo-url URL
  GitHub repository URL (required)
  Example: https://github.com/user/repo

--branch NAME
  Branch name to fetch files from (default: main)
  Example: develop, main, release/v1.0

--target-paths PATTERN [PATTERN ...]
  Glob patterns for target files (required, can specify multiple)
  Examples: "docs/**/*.md", "README.md", "**/*.md"

--languages LANG [LANG ...]
  Target languages for translation (required, can specify multiple)
  Examples: en, zh-CN, zh-TW, ko, fr, de, es

--glossary-path PATH
  Path to glossary JSON file (required)
  Example: ./glossary.json, /path/to/terms.json

--output-root DIR
  Output directory for translated files (default: ./output)
  Example: ./translations, /tmp/output

--push-option OPTION
  GitHub push strategy (default: none)
  Options:
    - none: Save locally only (no GitHub operations)
    - push_same_repo_direct: Push to same branch (requires confirmation)
    - push_same_repo_new_branch: Create new branch and push automatically

--output-naming MODE
  File naming convention (default: suffix)
  Options:
    - suffix: Output as file.en.md, file.zh-CN.md
    - directory: Output as /en/file.md, /zh-CN/file.md
```

## Glossary Format

Create a JSON glossary file with term mappings for consistent terminology:

### Basic Format

```json
{
  "terms": [
    {
      "ja": "帳票定義",
      "en": "Template Form",
      "zh-CN": "报表定义",
      "zh-TW": "表單定義"
    },
    {
      "ja": "ワークフロー",
      "en": "Workflow",
      "zh-CN": "工作流",
      "zh-TW": "工作流程"
    },
    {
      "ja": "ユーザーインターフェース",
      "en": "User Interface",
      "zh-CN": "用户界面",
      "zh-TW": "使用者介面"
    }
  ]
}
```

### Glossary Guidelines

- **Japanese (ja)**: Source term in Japanese
- **Language codes**: Use standard language codes (en, zh-CN, zh-TW, ko, fr, de, es, etc.)
- **Consistency**: All occurrences of a glossary term will be translated to the exact specified translation
- **Product names**: Include product names, feature names, and UI labels that should not be translated
- **Technical terms**: Include technical identifiers, commands, and API terms
- **Partial matches**: Glossary matching is exact - partial matches are not translated

### Example with Product Names

```json
{
  "terms": [
    {
      "ja": "GitBook",
      "en": "GitBook",
      "zh-CN": "GitBook",
      "zh-TW": "GitBook"
    },
    {
      "ja": "ドキュメント管理システム",
      "en": "Document Management System",
      "zh-CN": "文档管理系统",
      "zh-TW": "文件管理系統"
    }
  ]
}
```

## Agent Behavior and Tool Usage

### Translation Workflow

The GitBook Translator Agent follows this workflow:

1. **Fetch Files**: Uses `FetchGitHubFilesTool` to retrieve files from the GitHub repository
2. **Detect Changes**: Uses `DetectFileChangesTool` to identify new and modified files (skips unchanged files)
3. **Load Glossary**: Uses `LoadGlossaryTool` to load and parse the glossary file
4. **For Each File and Language**:
   - **Parse Markdown**: Uses `ParseMarkdownTool` to identify protected regions (code blocks, URLs, tags, etc.)
   - **Translate**: Uses `TranslateContentTool` to translate Japanese text while preserving format
   - **Review**: Uses `ReviewTranslationTool` to verify quality and identify issues
   - **Correct** (if needed): Uses `CorrectTranslationTool` to fix critical issues (up to 2 iterations)
   - **Save**: Uses `SaveTranslationTool` to write translated files locally
5. **Push** (optional): Uses `PushToGitHubTool` to push translations to GitHub
6. **Log**: Uses `LogProgressTool` to track progress and report results

### Tool Descriptions

#### FetchGitHubFilesTool
Fetches Markdown files from a GitHub repository using glob patterns. Supports authentication for private repositories and handles rate limiting with exponential backoff.

#### DetectFileChangesTool
Compares current files with cached metadata to identify new, modified, and unchanged files. Minimizes LLM token consumption by skipping unchanged files.

#### ParseMarkdownTool
Parses Markdown and identifies protected regions that must not be translated:
- YAML frontmatter
- Fenced code blocks (```)
- Inline code (`)
- GitBook tags ({% %}, {{ }})
- HTML tags and attributes
- URLs in links and images
- Anchor links and file references

#### LoadGlossaryTool
Loads and parses glossary files (JSON format). Auto-detects glossary structure and provides term lookups for consistent terminology.

#### TranslateContentTool
Translates Japanese text to target language using LLM (OpenAI or Anthropic). Applies glossary terms, preserves format, and maintains structure information.

#### ReviewTranslationTool
Reviews translations for quality and completeness. Verifies:
- Format preservation (GitBook syntax, line breaks, indentation)
- Completeness (no untranslated Japanese text)
- Terminology consistency (glossary terms used correctly)
- Link preservation (URLs, paths, anchors unchanged)
- Language appropriateness (formal, natural tone)

Issues are classified by severity:
- **BLOCKER**: Structural damage, link corruption, missing content
- **MAJOR**: Semantic errors, glossary violations, untranslated Japanese
- **MINOR**: Stylistic improvements

#### CorrectTranslationTool
Corrects translations based on review feedback. Focuses on specific issues identified by the reviewer while minimizing changes to non-problematic sections.

#### SaveTranslationTool
Saves translated files locally with configurable naming conventions:
- **Suffix mode**: `docs/intro.md` → `output/docs/intro.en.md`
- **Directory mode**: `docs/intro.md` → `output/en/docs/intro.md`

#### PushToGitHubTool
Pushes translated files to GitHub repository. Supports:
- Local-only mode (no push)
- Direct push to same branch (with confirmation)
- New branch creation with automatic push

#### LogProgressTool
Logs progress, errors, and issues throughout the translation process. Provides:
- Progress tracking (current file, language, stage)
- Error logging with context
- Issue logging with severity and location
- Summary reporting with statistics

### Agent Reasoning Process

The agent uses ReAct (Reasoning + Acting) framework:

1. **Thought**: Agent analyzes the current state and decides the next action
2. **Action**: Agent calls a tool with appropriate parameters
3. **Observation**: Agent receives tool output and updates internal state
4. **Repeat**: Agent continues until all files and languages are processed

Example agent reasoning:

```
Thought: I need to fetch files from the repository first to see what needs to be translated.
Action: Call FetchGitHubFilesTool with repo_url, branch, and target_paths
Observation: Retrieved 5 Markdown files from the repository

Thought: Now I should detect which files have changed since the last run to minimize processing.
Action: Call DetectFileChangesTool with current files and cached metadata
Observation: 2 files are new, 1 file is modified, 2 files are unchanged

Thought: I should load the glossary before starting translation.
Action: Call LoadGlossaryTool with glossary_path
Observation: Loaded glossary with 25 terms for English, Chinese, and Korean

Thought: Now I'll process the first changed file for English translation.
Action: Call ParseMarkdownTool to identify protected regions
Observation: Identified 3 code blocks, 2 links, and 1 YAML frontmatter

Thought: Now I'll translate the content.
Action: Call TranslateContentTool with parsed segments and glossary
Observation: Translation completed successfully

Thought: I should review the translation for quality.
Action: Call ReviewTranslationTool with original and translated content
Observation: Found 1 MAJOR issue - untranslated Japanese text in one section

Thought: I need to correct this issue.
Action: Call CorrectTranslationTool with the identified issue
Observation: Correction completed

Thought: Let me review the corrected translation.
Action: Call ReviewTranslationTool again
Observation: No critical issues found - translation approved

Thought: Now I'll save the translation.
Action: Call SaveTranslationTool with translated content and output path
Observation: File saved successfully to output/docs/intro.en.md
```

## Troubleshooting

### Common Issues

#### "OPENAI_API_KEY or GOOGLE_API_KEY environment variable must be set"

**Solution**: Set your API keys in `.env` file:
```bash
cp .env.example .env
# Edit .env and add your API keys
export OPENAI_API_KEY=your_openai_key_here
export GOOGLE_API_KEY=your_google_key_here
```

#### "Invalid GitHub repository URL"

**Solution**: Ensure the repository URL is in correct format:
```bash
# Correct format
https://github.com/owner/repo

# Incorrect formats
github.com/owner/repo  # Missing https://
https://github.com/owner/repo/  # Trailing slash is OK
```

#### "Glossary file not found"

**Solution**: Verify the glossary file path:
```bash
# Check if file exists
ls -la ./glossary.json

# Use absolute path if relative path doesn't work
python -m src.cli --glossary-path /absolute/path/to/glossary.json ...
```

#### "Rate limit exceeded"

**Solution**: The agent automatically handles rate limiting with exponential backoff. If you still hit limits:
- Wait a few minutes before retrying
- Use a GitHub token with higher rate limits
- Process fewer files at once

#### "Translation timeout"

**Solution**: If translations are timing out:
- Increase `TRANSLATION_TIMEOUT` in `.env` (in seconds)
- Process smaller files first
- Check your LLM API status

#### "No files matched the target paths"

**Solution**: Verify your glob patterns:
```bash
# Check what files exist in the repository
# Use correct glob patterns
--target-paths "docs/**/*.md"  # Correct
--target-paths "docs/*.md"     # Only top-level files
--target-paths "**/*.md"       # All Markdown files
```

### Debug Mode

Enable LangChain tracing for detailed debugging:

```bash
# In .env file
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langchain_api_key

# Then run the agent
python -m src.cli ...
```

View traces at https://smith.langchain.com/

### Checking Logs

The agent logs all progress and errors. Check the output for:
- File processing status
- Translation issues and corrections
- Error messages with context
- Final summary with statistics

## Project Structure

```
gitbook-translator/
├── src/
│   ├── agent/
│   │   └── translation_agent.py      # LangChain ReAct Agent implementation
│   ├── tools/
│   │   ├── fetch_github_files.py      # GitHub file fetching tool
│   │   ├── detect_file_changes.py     # Diff detection tool
│   │   ├── parse_markdown.py          # Markdown parsing tool
│   │   ├── load_glossary.py           # Glossary loading tool
│   │   ├── translate_content.py       # Translation tool
│   │   ├── review_translation.py      # Review tool
│   │   ├── correct_translation.py     # Correction tool
│   │   ├── save_translation.py        # File saving tool
│   │   ├── push_to_github.py          # GitHub push tool
│   │   ├── log_progress.py            # Logging tool
│   │   └── __init__.py
│   ├── models/
│   │   ├── agent_models.py            # Agent state models
│   │   ├── file_models.py             # File-related models
│   │   ├── translation_models.py      # Translation models
│   │   ├── review_models.py           # Review models
│   │   ├── markdown_models.py         # Markdown models
│   │   ├── glossary_models.py         # Glossary models
│   │   ├── log_models.py              # Logging models
│   │   ├── config.py                  # Configuration models
│   │   └── __init__.py
│   ├── cli.py                         # Command-line interface
│   └── __init__.py
├── tests/                             # Test suite
├── .env.example                       # Example environment variables
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project configuration
└── README.md                          # This file
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_cli.py

# Run property-based tests
pytest tests/test_*_property.py -v
```

### Running Property-Based Tests

Property-based tests use Hypothesis to generate random inputs and verify correctness properties:

```bash
# Run all property tests
pytest tests/test_*_property.py -v

# Run specific property test
pytest tests/test_parse_markdown_property.py -v

# Run with more examples (default is 100)
pytest tests/test_parse_markdown_property.py -v --hypothesis-seed=0
```

### Code Style

The project follows PEP 8 style guidelines. Format code with:

```bash
black src/ tests/
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues, questions, or suggestions, please open an issue on GitHub or contact the maintainers.
