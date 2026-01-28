# Design Document / 設計書

## Overview / 概要

GitBook Translator is an AI Agent-based command-line tool that automates the translation of GitBook-formatted Markdown documentation from Japanese to multiple target languages while preserving all GitBook-specific syntax, structure, and formatting. The system is built using LangChain's Agent framework with custom tools and orchestrates complex translation workflows autonomously.

**Core Architecture**:
1. **Translation Agent**: A LangChain ReAct Agent that orchestrates the entire translation workflow using custom tools
2. **Custom Tools**: Specialized tools for GitHub operations, Markdown parsing, translation, review, and file management
3. **Agent Memory**: Maintains context across translation tasks and learns from corrections

The system uses an agentic approach where the Translation Agent autonomously:
- Fetches files from GitHub and detects changes
- Parses Markdown and identifies protected regions
- Translates content using Writer AI with glossary application
- Reviews translations using Reviewer AI
- Iteratively corrects issues based on review feedback
- Saves translated files and optionally pushes to GitHub

The agent prioritizes format preservation above all else, ensuring that translated documents remain fully compatible with GitBook. Diff detection minimizes LLM token consumption by processing only changed files.


## Architecture / アーキテクチャ

The system follows a pipeline architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                            │
│                    (Parameter Validation)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        File Manager                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   GitHub     │  │    Diff      │  │    Cache     │         │
│  │   Fetcher    │  │  Detection   │  │   Manager    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Translation Pipeline                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Markdown Parser                          │      │
│  │  (Protected Region Detection & Segmentation)          │      │
│  └────────────────────┬─────────────────────────────────┘      │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Writer AI                                │      │
│  │  (Translation with Glossary Application)              │      │
│  └────────────────────┬─────────────────────────────────┘      │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Reviewer AI                              │      │
│  │  (Quality Verification & Issue Classification)        │      │
│  └────────────────────┬─────────────────────────────────┘      │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │         Correction Loop (max 2 iterations)            │      │
│  └──────────────────────────────────────────────────────┘      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Output Manager                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │    File      │  │   Naming     │  │   GitHub     │         │
│  │   Writer     │  │  Convention  │  │   Pusher     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles / 主要な設計原則

1. **Format Preservation First**: All components prioritize maintaining the exact structure and syntax of the original Markdown
2. **Fail-Safe Processing**: Errors in one file or language do not prevent processing of others
3. **Minimal Token Usage**: Diff detection and protected region identification minimize LLM API calls
4. **Idempotency**: Running the tool multiple times on unchanged files produces no additional work
5. **Transparency**: Comprehensive logging and reporting at every stage

## Components and Interfaces / コンポーネントとインターフェース

### 1. CLI Interface / CLIインターフェース

**Responsibility**: Parse command-line arguments and validate input parameters

**Input Parameters**:
```python
from dataclasses import dataclass
from typing import List, Literal

@dataclass
class CLIConfig:
    repo_url: str           # GitHub repository URL
    branch: str             # Branch name (e.g., "main")
    target_paths: List[str] # Glob patterns (e.g., ["docs/**/*.md", "README.md"])
    languages: List[str]    # Target languages (e.g., ["en", "zh-CN", "zh-TW"])
    glossary_path: str      # Path to glossary JSON file
    output_root: str        # Local output directory
    push_option: Literal['none', 'push_same_repo_direct', 'push_same_repo_new_branch']
    output_naming: Literal['suffix', 'directory']  # <name>.<lang>.md or /en/name.md
```

**Validation Rules**:
- `repo_url` must be a valid GitHub URL
- `branch` must be non-empty
- `target_paths` must contain at least one pattern
- `languages` must contain at least one valid language code
- `glossary_path` must point to an existing JSON file
- `output_root` must be a valid directory path
- `push_option` defaults to 'none'
- `output_naming` defaults to 'suffix'

### 2. File Manager / ファイルマネージャー

**Responsibility**: Handle all file system and GitHub operations

#### 2.1 GitHub Fetcher / GitHub取得機能

**Interface**:
```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class FetchedFile:
    path: str              # Relative path in repository
    content: str           # File content
    commit_hash: str       # Current commit SHA
    last_modified: datetime  # Last modification timestamp

class GitHubFetcher:
    def fetch_files(
        self,
        repo_url: str,
        branch: str,
        target_paths: List[str],
        auth_token: Optional[str] = None
    ) -> List[FetchedFile]:
        pass
```

**Implementation Notes**:
- Use PyGithub or GitHub REST API for file fetching
- Support authentication via environment variable `GITHUB_TOKEN`
- Resolve glob patterns using fnmatch or pathlib
- Handle API rate limiting with exponential backoff
- Cache API responses to minimize requests

#### 2.2 Diff Detection / 差分検出

**Interface**:
```python
@dataclass
class FileMetadata:
    path: str
    commit_hash: str
    last_modified: datetime
    translated_languages: List[str]

@dataclass
class DiffResult:
    new_files: List[FetchedFile]
    modified_files: List[FetchedFile]
    unchanged_files: List[FetchedFile]

class DiffDetector:
    def detect_changes(
        self,
        current_files: List[FetchedFile],
        cached_metadata: List[FileMetadata]
    ) -> DiffResult:
        pass
```

**Implementation Notes**:
- Store metadata in `.gitbook-translator-cache.json` in output_root
- Compare commit hashes for change detection
- Mark translations as outdated when source changes
- First run treats all files as new

#### 2.3 Cache Manager / キャッシュマネージャー

**Interface**:
```python
class CacheManager:
    def load_cache(self, output_root: str) -> List[FileMetadata]:
        pass
    
    def save_cache(self, output_root: str, metadata: List[FileMetadata]) -> None:
        pass
    
    def update_metadata(self, file: FetchedFile, languages: List[str]) -> FileMetadata:
        pass
```

### 3. Translation Pipeline / 翻訳パイプライン

**Responsibility**: Orchestrate the translation workflow

#### 3.1 Markdown Parser / Markdownパーサー

**Interface**:
```python
from typing import Dict, Optional
from enum import Enum

class SegmentType(Enum):
    PROTECTED = "protected"
    TRANSLATABLE = "translatable"

@dataclass
class SegmentMetadata:
    protection_reason: Optional[str] = None  # 'code-block' | 'inline-code' | 'url' | 'yaml' | 'gitbook-tag' | 'html'
    link_url: Optional[str] = None
    alt_text: Optional[str] = None

@dataclass
class Segment:
    type: SegmentType
    content: str
    start_line: int
    end_line: int
    metadata: Optional[SegmentMetadata] = None

@dataclass
class StructureInfo:
    line_breaks: List[int]              # Line numbers where breaks occur
    indentation: Dict[int, int]         # Line number -> indent level
    whitespace: Dict[int, str]          # Line number -> whitespace pattern

@dataclass
class ParsedMarkdown:
    segments: List[Segment]
    structure: StructureInfo

class MarkdownParser:
    def parse(self, content: str) -> ParsedMarkdown:
        pass
```

**Protected Region Detection Rules**:
1. YAML frontmatter: `---` to `---`
2. Fenced code blocks: ` ``` ` to ` ``` `
3. Inline code: `` ` `` to `` ` ``
4. GitBook tags: `{% ... %}`, `{{ ... }}`
5. HTML tags and attributes
6. URLs in links: `[text](URL)` - protect URL only
7. Image paths: `![alt](path)` - protect path only
8. Anchor links: `#...`
9. File references

**Implementation Notes**:
- Use regex patterns for initial detection
- Build a state machine for nested structures
- Preserve exact character positions for reconstruction
- Handle edge cases like escaped backticks

#### 3.2 Glossary Manager / 用語集マネージャー

**Interface**:
```python
@dataclass
class Glossary:
    format: Literal['auto-detected', 'custom']
    mappings: Dict[str, Dict[str, str]]  # term -> (language -> translation)

class GlossaryManager:
    def load_glossary(self, path: str) -> Glossary:
        pass
    
    def get_translation(self, term: str, target_lang: str) -> Optional[str]:
        pass
```

**Glossary Format Detection**:
- Support common formats: JSON with language keys, CSV with language columns
- Auto-detect structure by analyzing keys/columns
- Example JSON format:
```json
{
  "terms": [
    {
      "ja": "帳票定義",
      "en": "Template Form",
      "zh-CN": "报表定义",
      "zh-TW": "表單定義"
    }
  ]
}
```

#### 3.3 Writer AI / ライターAI

**Interface**:
```python
@dataclass
class TranslationRequest:
    segments: List[Segment]
    target_language: str
    glossary: Glossary
    structure: StructureInfo

@dataclass
class TranslationResult:
    translated_segments: List[Segment]
    reconstructed_content: str

class WriterAI:
    def translate(self, request: TranslationRequest) -> TranslationResult:
        pass
```

**Translation Prompt Template (LangChain)**:
```python
from langchain.prompts import ChatPromptTemplate

translation_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a professional translator specializing in technical documentation.

Task: Translate the following Japanese text segments to {target_language}.

Critical Rules:
1. Translate ONLY the Japanese text in the provided segments
2. Preserve ALL formatting, line breaks, indentation, and spacing exactly
3. Do NOT translate protected regions (code, URLs, tags, etc.)
4. Use formal, polite, business-appropriate tone
5. Apply glossary terms exactly as specified
6. Maintain semantic accuracy and clarity

Glossary Terms:
{glossary_terms}"""),
    ("user", """Segments to Translate:
{segments}

Output the translated segments in the same structure.""")
])
```

**Implementation Notes**:
- Use LangChain with ChatOpenAI or ChatAnthropic for high-quality translation
- Use LangChain's PromptTemplate for structured prompts
- Include structure information in the prompt
- Validate output structure matches input
- Use LangChain's retry logic with exponential backoff

#### 3.4 Reviewer AI / レビューアーAI

**Interface**:
```python
from enum import Enum

class IssueSeverity(Enum):
    BLOCKER = "BLOCKER"
    MAJOR = "MAJOR"
    MINOR = "MINOR"

class IssueCategory(Enum):
    FORMAT = "format"
    COMPLETENESS = "completeness"
    TERMINOLOGY = "terminology"
    LINKS = "links"
    STYLE = "style"

@dataclass
class IssueLocation:
    line: int
    column: Optional[int] = None

@dataclass
class Issue:
    severity: IssueSeverity
    category: IssueCategory
    location: IssueLocation
    description: str
    suggestion: Optional[str] = None

@dataclass
class ReviewRequest:
    original_content: str
    translated_content: str
    target_language: str
    glossary: Glossary

@dataclass
class ReviewResult:
    issues: List[Issue]
    approved: bool

class ReviewerAI:
    def review(self, request: ReviewRequest) -> ReviewResult:
        pass
```

**Review Prompt Template (LangChain)**:
```python
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

review_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a quality assurance reviewer for technical documentation translation.

Task: Review the translation for quality and completeness.

Verification Checklist:
1. Format Preservation: GitBook syntax, tags, line breaks, indentation, tables, code blocks
2. Completeness: No untranslated Japanese text, no missing lines
3. Terminology: Glossary terms used consistently
4. Links: URLs, paths, anchors unchanged
5. Style: Formal, natural language appropriate for {target_language}

Glossary:
{glossary_terms}

{format_instructions}"""),
    ("user", """Original Content:
{original_content}

Translated Content:
{translated_content}

Output issues in JSON format with severity (BLOCKER/MAJOR/MINOR), category, location, description, and suggestion.""")
])
```

**Issue Classification**:
- **BLOCKER**: Structural damage, link corruption, missing content, code modification
- **MAJOR**: Semantic errors, glossary violations, untranslated Japanese
- **MINOR**: Stylistic improvements

#### 3.5 Correction Loop / 修正ループ

**Logic**:
```python
def translate_with_review(
    content: str,
    target_lang: str,
    glossary: Glossary,
    writer_ai: WriterAI,
    reviewer_ai: ReviewerAI,
    max_iterations: int = 2
) -> str:
    translated_content = writer_ai.translate(
        TranslationRequest(
            segments=parse_segments(content),
            target_language=target_lang,
            glossary=glossary,
            structure=extract_structure(content)
        )
    ).reconstructed_content
    
    for i in range(max_iterations):
        review = reviewer_ai.review(
            ReviewRequest(
                original_content=content,
                translated_content=translated_content,
                target_language=target_lang,
                glossary=glossary
            )
        )
        
        critical_issues = [
            issue for issue in review.issues
            if issue.severity in [IssueSeverity.BLOCKER, IssueSeverity.MAJOR]
        ]
        
        if len(critical_issues) == 0:
            return translated_content
        
        # Request corrections for critical issues only
        translated_content = writer_ai.correct(
            content=translated_content,
            issues=critical_issues
        )
    
    # Proceed with current version after max iterations
    return translated_content
```

### 4. Output Manager / 出力マネージャー

**Responsibility**: Save translated files and optionally push to GitHub

#### 4.1 File Writer / ファイルライター

**Interface**:
```python
@dataclass
class SaveRequest:
    original_path: str
    content: str
    language: str
    output_root: str
    naming_convention: Literal['suffix', 'directory']

@dataclass
class SaveResult:
    saved_path: str
    success: bool
    error: Optional[str] = None

class FileWriter:
    def save_translation(self, request: SaveRequest) -> SaveResult:
        pass
```

**Naming Convention Logic**:
- **Suffix mode**: `docs/intro.md` → `{output_root}/docs/intro.en.md`
- **Directory mode**: `docs/intro.md` → `{output_root}/en/docs/intro.md`

**Implementation Notes**:
- Create parent directories automatically using `pathlib.Path.mkdir(parents=True, exist_ok=True)`
- Preserve relative directory structure from source
- Handle file write errors gracefully

#### 4.2 GitHub Pusher / GitHubプッシャー

**Interface**:
```python
@dataclass
class FileContent:
    path: str
    content: str

@dataclass
class PushRequest:
    repo_url: str
    branch: str
    files: List[FileContent]
    push_option: Literal['push_same_repo_direct', 'push_same_repo_new_branch']
    auth_token: str

@dataclass
class PushResult:
    success: bool
    branch_name: Optional[str] = None
    pr_url: Optional[str] = None
    error: Optional[str] = None

class GitHubPusher:
    def push(self, request: PushRequest) -> PushResult:
        pass
```

**Push Logic**:
- **none**: Skip GitHub operations
- **push_same_repo_direct**: Request explicit confirmation, then push to same branch
- **push_same_repo_new_branch**: Create branch `translation/{lang}/{timestamp}`, push, provide PR info

**Implementation Notes**:
- Use GitHub API for branch creation and file updates
- Handle conflicts by reporting error
- Provide clear PR creation instructions

### 5. Logger / ロガー

**Interface**:
```python
@dataclass
class LogContext:
    file: Optional[str] = None
    language: Optional[str] = None
    operation: Optional[str] = None

@dataclass
class ProcessingSummary:
    files_processed: int
    translations_created: int
    errors: int
    warnings: int
    duration: float

class Logger:
    def log_progress(self, stage: str, file: str, language: str) -> None:
        pass
    
    def log_error(self, error: Exception, context: LogContext) -> None:
        pass
    
    def log_issue(self, issue: Issue) -> None:
        pass
    
    def log_summary(self, summary: ProcessingSummary) -> None:
        pass
```

## Data Models / データモデル

### File Metadata Cache / ファイルメタデータキャッシュ

```json
{
  "version": "1.0",
  "lastRun": "2026-01-16T10:30:00Z",
  "files": [
    {
      "path": "docs/intro.md",
      "commitHash": "abc123...",
      "lastModified": "2026-01-15T14:20:00Z",
      "translatedLanguages": ["en", "zh-CN"],
      "translations": {
        "en": {
          "outputPath": "output/docs/intro.en.md",
          "translatedAt": "2026-01-16T10:25:00Z"
        },
        "zh-CN": {
          "outputPath": "output/zh-CN/docs/intro.md",
          "translatedAt": "2026-01-16T10:28:00Z"
        }
      }
    }
  ]
}
```

### Processing State / 処理状態

```python
@dataclass
class ProcessingState:
    config: CLIConfig
    fetched_files: List[FetchedFile]
    diff_result: DiffResult
    glossary: Glossary
    current_file: Optional[str] = None
    current_language: Optional[str] = None
    results: Dict[str, Dict[str, TranslationResult]] = None  # file -> (lang -> result)
    errors: List[Exception] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = {}
        if self.errors is None:
            self.errors = []
```

## Correctness Properties / 正確性プロパティ

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Whitespace preservation
*For any* Markdown file, after translation, all line breaks, blank lines, indentation, and spacing should be identical to the original.
**Validates: Requirements 3.1**

### Property 2: Protected region round-trip
*For any* Markdown file containing protected regions (code blocks, inline code, YAML frontmatter, GitBook tags, HTML tags, template expressions), those regions should be byte-identical after translation.
**Validates: Requirements 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.5**

### Property 3: Link URL preservation
*For any* Markdown file containing links `[text](URL)`, all URLs should remain unchanged after translation while display text containing Japanese should be translated.
**Validates: Requirements 5.1**

### Property 4: Image path preservation
*For any* Markdown file containing images `![alt](path)`, all paths should remain unchanged after translation while alt text containing Japanese should be translated.
**Validates: Requirements 5.2**

### Property 5: Relative path preservation
*For any* Markdown file containing relative paths, anchor links, or file references, all such references should remain unchanged after translation.
**Validates: Requirements 5.3, 5.4, 5.5**

### Property 6: Table structure preservation
*For any* Markdown file containing tables, after translation, the number of columns, pipe characters, and alignment markers should be identical to the original.
**Validates: Requirements 6.1, 6.3, 6.4**

### Property 7: Table cell translation
*For any* Markdown table with Japanese content in cells, after translation, only cell content should be translated while maintaining the exact column structure.
**Validates: Requirements 6.2**

### Property 8: Japanese-only translation
*For any* text segment, only portions containing Japanese characters (Unicode ranges U+3040-U+309F, U+30A0-U+30FF, U+4E00-U+9FFF) should be translated, while non-Japanese text should remain unchanged.
**Validates: Requirements 7.1, 7.2, 7.3, 7.4**

### Property 9: Punctuation preservation
*For any* text containing punctuation and symbols, their usage and positioning should be preserved after translation.
**Validates: Requirements 7.5**

### Property 10: Glossary term consistency
*For any* text containing a glossary term, all occurrences of that term should be translated to the exact same target language translation specified in the glossary.
**Validates: Requirements 8.3, 8.4**

### Property 11: Technical term preservation
*For any* text containing product names, feature names, UI labels, commands, or technical identifiers not in the glossary, those terms should remain untranslated.
**Validates: Requirements 8.5**

### Property 12: Markdown validity preservation
*For any* valid Markdown file, after translation, the output should be valid Markdown that can be parsed without errors.
**Validates: Requirements 9.5**

### Property 13: Complete translation
*For any* translated Markdown file, there should be no remaining untranslated Japanese text outside of protected regions.
**Validates: Requirements 10.2**

### Property 14: Diff detection accuracy
*For any* file with unchanged commit hash, the system should skip it from the translation queue; for any file with changed commit hash, the system should add it to the translation queue.
**Validates: Requirements 2.3, 2.4**

### Property 15: File naming consistency
*For any* translated file in suffix mode, the output filename should follow the pattern `<name>.<lang>.md`; in directory mode, it should be saved in `/<lang>/<original-path>`.
**Validates: Requirements 13.1, 13.2**

### Property 16: Directory structure preservation
*For any* source file with relative directory structure, the translated output should preserve that structure relative to the output root.
**Validates: Requirements 13.4**

### Property 17: Multi-language glossary application
*For any* text translated to multiple target languages, each language should use its corresponding glossary mappings from the glossary file.
**Validates: Requirements 15.2**

### Property 18: Error isolation
*For any* processing run with multiple files or languages, an error in one file or language should not prevent processing of remaining files or languages.
**Validates: Requirements 15.4**

### Property 19: Log completeness
*For any* error encountered during processing, the log should contain the error message, file path, target language, and operation context.
**Validates: Requirements 16.1**

### Property 20: Progress logging
*For any* file being processed, the log should contain entries indicating the current file, language, and processing stage.
**Validates: Requirements 16.2**

## Error Handling / エラーハンドリング

### Error Categories / エラーカテゴリ

1. **GitHub API Errors**
   - Rate limiting: Implement exponential backoff
   - Authentication failures: Report clear error with token setup instructions
   - Network errors: Retry up to 3 times
   - Repository not found: Report error and halt

2. **File System Errors**
   - Permission denied: Report error with file path
   - Disk full: Report error and halt
   - Invalid path: Report error and skip file

3. **Translation Errors**
   - LLM API failures: Retry up to 3 times with exponential backoff
   - Invalid response format: Log error and request re-translation
   - Timeout: Increase timeout and retry once

4. **Validation Errors**
   - Invalid configuration: Report specific validation error and halt
   - Glossary parse error: Report error with file path and halt
   - Markdown parse error: Log error and skip file

### Error Recovery Strategy / エラー回復戦略

- **Fail-fast**: Configuration and glossary errors halt immediately
- **Fail-safe**: File-level errors skip the file and continue
- **Retry with backoff**: Network and API errors retry with exponential backoff
- **Graceful degradation**: After max correction iterations, proceed with current translation
- **Comprehensive logging**: All errors logged with full context

## Testing Strategy / テスト戦略

### Unit Testing / ユニットテスト

**Test Coverage Areas**:
1. **Markdown Parser**: Test protected region detection with various edge cases
2. **Glossary Manager**: Test format detection and term lookup
3. **File Writer**: Test naming convention logic
4. **Diff Detector**: Test change detection logic
5. **Logger**: Test log formatting and output

**Example Unit Tests**:
- Parse Markdown with nested code blocks
- Detect YAML frontmatter boundaries
- Apply glossary terms in mixed-language text
- Generate correct output paths for both naming conventions
- Detect file changes based on commit hash

### Property-Based Testing / プロパティベーステスト

**Property Testing Library**: Use `hypothesis` for Python

**Test Configuration**: Each property test should run a minimum of 100 iterations using `@settings(max_examples=100)`

**Property Test Tagging**: Each property-based test must include a comment with the format:
`# Feature: gitbook-translator, Property {number}: {property_text}`

**Property Tests to Implement**:

1. **Whitespace Preservation Property**
   - Generate random Markdown with various whitespace patterns
   - Translate and verify whitespace is identical
   - Tag: `# Feature: gitbook-translator, Property 1: Whitespace preservation`

2. **Protected Region Round-Trip Property**
   - Generate random Markdown with code blocks, inline code, YAML, tags
   - Translate and verify protected regions are byte-identical
   - Tag: `# Feature: gitbook-translator, Property 2: Protected region round-trip`

3. **Link URL Preservation Property**
   - Generate random Markdown with various link formats
   - Translate and verify URLs unchanged, display text translated
   - Tag: `# Feature: gitbook-translator, Property 3: Link URL preservation`

4. **Table Structure Preservation Property**
   - Generate random Markdown tables with various column counts
   - Translate and verify column count and structure unchanged
   - Tag: `# Feature: gitbook-translator, Property 6: Table structure preservation`

5. **Japanese-Only Translation Property**
   - Generate random mixed-language text
   - Translate and verify only Japanese portions changed
   - Tag: `# Feature: gitbook-translator, Property 8: Japanese-only translation`

6. **Glossary Term Consistency Property**
   - Generate random text with repeated glossary terms
   - Translate and verify all occurrences use same translation
   - Tag: `# Feature: gitbook-translator, Property 10: Glossary term consistency`

7. **Markdown Validity Property**
   - Generate random valid Markdown
   - Translate and verify output is valid Markdown
   - Tag: `# Feature: gitbook-translator, Property 12: Markdown validity preservation`

8. **Complete Translation Property**
   - Generate random Markdown with Japanese text
   - Translate and verify no Japanese remains outside protected regions
   - Tag: `# Feature: gitbook-translator, Property 13: Complete translation`

9. **File Naming Consistency Property**
   - Generate random file paths
   - Verify output paths follow naming convention
   - Tag: `# Feature: gitbook-translator, Property 15: File naming consistency`

10. **Multi-Language Glossary Property**
    - Generate random text with glossary terms
    - Translate to multiple languages
    - Verify each uses correct language-specific glossary mapping
    - Tag: `# Feature: gitbook-translator, Property 17: Multi-language glossary application`

### Integration Testing / 統合テスト

**Test Scenarios**:
1. End-to-end translation of sample GitBook documentation
2. Diff detection with simulated file changes
3. Multi-language translation workflow
4. Error recovery scenarios (API failures, invalid files)
5. GitHub push operations (using test repository)

### Test Data / テストデータ

**Sample Files**:
- Simple Markdown with Japanese text
- Complex GitBook documentation with all syntax features
- Markdown with edge cases (nested code blocks, complex tables)
- Invalid Markdown for error handling tests
- Sample glossary files in various formats

**Mock Services**:
- Mock GitHub API for file fetching
- Mock LLM API for translation and review
- Mock file system for I/O operations

## Performance Considerations / パフォーマンス考慮事項

### Optimization Strategies / 最適化戦略

1. **Diff Detection**: Skip unchanged files to minimize LLM API calls
2. **Batch Processing**: Process multiple segments in single LLM API call when possible
3. **Caching**: Cache GitHub API responses and file metadata
4. **Parallel Processing**: Process multiple languages in parallel (optional enhancement)
5. **Incremental Updates**: Only re-translate changed portions (future enhancement)

### Resource Limits / リソース制限

- **LLM Token Limits**: Split large files into chunks if needed
- **GitHub API Rate Limits**: Implement rate limiting and backoff
- **Memory Usage**: Stream large files instead of loading entirely into memory
- **Disk Space**: Verify sufficient space before writing output

## Security Considerations / セキュリティ考慮事項

1. **GitHub Token**: Store in environment variable, never in code or logs
2. **Input Validation**: Validate all user inputs to prevent injection attacks
3. **Path Traversal**: Sanitize file paths to prevent directory traversal
4. **API Key Protection**: Mask LLM API keys in logs and error messages
5. **Dependency Security**: Regularly update dependencies and scan for vulnerabilities

## Future Enhancements / 将来の拡張

1. **Incremental Translation**: Translate only changed paragraphs within files
2. **Parallel Processing**: Process multiple languages simultaneously
3. **Translation Memory**: Reuse previous translations for repeated content
4. **Custom AI Models**: Support for custom fine-tuned translation models
5. **Web UI**: Browser-based interface for configuration and monitoring
6. **Webhook Integration**: Automatic translation on GitHub push events
7. **Quality Metrics**: Automated quality scoring for translations
8. **Terminology Extraction**: Automatic glossary term suggestion
