# AI Agent Design Document / AI Agent設計書

## Overview / 概要

GitBook Translator は、LangChainのAgentフレームワークを使用して構築されたAI Agent型の翻訳システムです。Translation Agentが自律的に判断しながら、GitBook形式のMarkdownドキュメントを日本語から複数の言語へ翻訳します。

**コアアーキテクチャ**:
1. **Translation Agent (ReAct Agent)**: LangChainのReActパターンを使用し、推論と行動を繰り返しながら翻訳ワークフローを自律的に実行
2. **Custom Tools**: Agent が使用する専用ツール群（GitHub操作、Markdown解析、翻訳、レビュー、ファイル管理）
3. **Agent Memory**: ConversationBufferMemoryを使用して、翻訳タスク間のコンテキストを保持し、修正から学習

**Agent の自律的な動作**:
- GitHubからファイルを取得し、差分を検出
- Markdownを解析し、保護領域を識別
- 用語集を適用しながらWriter AIで翻訳
- Reviewer AIで翻訳品質を検証
- レビューフィードバックに基づいて反復的に修正
- 翻訳ファイルを保存し、オプションでGitHubにプッシュ

システムは形式保持を最優先し、翻訳されたドキュメントがGitBookと完全に互換性を保つことを保証します。

## Architecture / アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                            │
│                    (Parameter Validation)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Translation Agent (ReAct)                     │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Agent Memory & State                       │    │
│  │  - ConversationBufferMemory                             │    │
│  │  - Processing State Tracking                            │    │
│  │  - Error History                                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Agent Tools                                │    │
│  │                                                          │    │
│  │  1. FetchGitHubFilesTool                               │    │
│  │  2. DetectFileChangesTool                              │    │
│  │  3. ParseMarkdownTool                                  │    │
│  │  4. LoadGlossaryTool                                   │    │
│  │  5. TranslateContentTool                               │    │
│  │  6. ReviewTranslationTool                              │    │
│  │  7. CorrectTranslationTool                             │    │
│  │  8. SaveTranslationTool                                │    │
│  │  9. PushToGitHubTool                                   │    │
│  │  10. LogProgressTool                                   │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Agent Reasoning Loop                       │    │
│  │  Thought → Action → Observation → Thought → ...        │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Workflow / Agentワークフロー

Translation Agentは以下の推論ループを実行します：

```
1. Thought: "I need to fetch files from GitHub repository"
   Action: Use FetchGitHubFilesTool
   Observation: Retrieved 10 markdown files

2. Thought: "I should check which files have changed since last run"
   Action: Use DetectFileChangesTool
   Observation: 3 files are new, 2 files are modified, 5 files unchanged

3. Thought: "I need to load the glossary for consistent terminology"
   Action: Use LoadGlossaryTool
   Observation: Loaded glossary with 50 terms

4. For each file to translate:
   a. Thought: "I need to parse this markdown and identify protected regions"
      Action: Use ParseMarkdownTool
      Observation: Found 5 code blocks, 3 links, 2 images to protect
   
   b. Thought: "Now I can translate the Japanese text to English"
      Action: Use TranslateContentTool
      Observation: Translation completed
   
   c. Thought: "I should review the translation for quality"
      Action: Use ReviewTranslationTool
      Observation: Found 2 MAJOR issues with glossary terms
   
   d. Thought: "I need to correct the identified issues"
      Action: Use CorrectTranslationTool
      Observation: Corrections applied
   
   e. Thought: "Let me review again to ensure quality"
      Action: Use ReviewTranslationTool
      Observation: No critical issues found, translation approved
   
   f. Thought: "I can now save the translated file"
      Action: Use SaveTranslationTool
      Observation: File saved to output/docs/intro.en.md

5. Thought: "All translations complete, should I push to GitHub?"
   Action: Check push_option configuration
   Observation: push_option is 'push_same_repo_new_branch'
   
6. Thought: "I'll create a new branch and push the translations"
   Action: Use PushToGitHubTool
   Observation: Created branch translation/en/20260116_103000, pushed 5 files

7. Thought: "Task complete, I should log the summary"
   Action: Use LogProgressTool
   Observation: Summary logged - 5 files processed, 5 translations created, 0 errors
```

## Agent Tools / Agentツール

### 1. FetchGitHubFilesTool

**Purpose**: GitHubリポジトリからMarkdownファイルを取得

**Input Schema**:
```python
class FetchGitHubFilesInput(BaseModel):
    repo_url: str = Field(description="GitHub repository URL")
    branch: str = Field(description="Branch name")
    target_paths: List[str] = Field(description="Glob patterns for files to fetch")
    auth_token: Optional[str] = Field(description="GitHub authentication token")
```

**Output**: List of FetchedFile objects with path, content, commit_hash, last_modified

**Implementation**:
- Use PyGithub API
- Resolve glob patterns
- Handle rate limiting
- Cache responses

### 2. DetectFileChangesTool

**Purpose**: 前回処理からの変更ファイルを検出

**Input Schema**:
```python
class DetectFileChangesInput(BaseModel):
    current_files: List[Dict] = Field(description="Current fetched files")
    output_root: str = Field(description="Output directory for cache")
```

**Output**: DiffResult with new_files, modified_files, unchanged_files

**Implementation**:
- Load cache from `.gitbook-translator-cache.json`
- Compare commit hashes
- Return categorized file lists

### 3. ParseMarkdownTool

**Purpose**: Markdownを解析し、保護領域と翻訳可能領域を識別

**Input Schema**:
```python
class ParseMarkdownInput(BaseModel):
    content: str = Field(description="Markdown content to parse")
```

**Output**: ParsedMarkdown with segments and structure info

**Implementation**:
- Detect YAML frontmatter, code blocks, inline code
- Detect GitBook tags, HTML tags, template expressions
- Identify links, images, anchors
- Preserve whitespace and indentation info

### 4. LoadGlossaryTool

**Purpose**: 用語集を読み込み、翻訳時の用語統一を準備

**Input Schema**:
```python
class LoadGlossaryInput(BaseModel):
    glossary_path: str = Field(description="Path to glossary JSON file")
```

**Output**: Glossary object with term mappings

**Implementation**:
- Auto-detect glossary format
- Parse JSON/CSV formats
- Build term -> language -> translation mapping

### 5. TranslateContentTool

**Purpose**: Writer AIを使用してコンテンツを翻訳

**Input Schema**:
```python
class TranslateContentInput(BaseModel):
    segments: List[Dict] = Field(description="Parsed markdown segments")
    target_language: str = Field(description="Target language code")
    glossary: Dict = Field(description="Glossary mappings")
    structure: Dict = Field(description="Structure information")
```

**Output**: TranslationResult with translated_segments and reconstructed_content

**Implementation**:
- Use LangChain ChatOpenAI/ChatAnthropic
- Apply translation prompt template
- Apply glossary terms
- Preserve protected regions
- Reconstruct full content

**Prompt Template**:
```python
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

### 6. ReviewTranslationTool

**Purpose**: Reviewer AIを使用して翻訳品質を検証

**Input Schema**:
```python
class ReviewTranslationInput(BaseModel):
    original_content: str = Field(description="Original markdown content")
    translated_content: str = Field(description="Translated markdown content")
    target_language: str = Field(description="Target language code")
    glossary: Dict = Field(description="Glossary mappings")
```

**Output**: ReviewResult with issues list and approved boolean

**Implementation**:
- Use LangChain ChatOpenAI/ChatAnthropic
- Apply review prompt template
- Use PydanticOutputParser for structured output
- Classify issues by severity (BLOCKER, MAJOR, MINOR)

**Prompt Template**:
```python
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

### 7. CorrectTranslationTool

**Purpose**: レビューで指摘された問題を修正

**Input Schema**:
```python
class CorrectTranslationInput(BaseModel):
    content: str = Field(description="Translated content to correct")
    issues: List[Dict] = Field(description="Issues to fix")
```

**Output**: Corrected translation content

**Implementation**:
- Use LangChain ChatOpenAI/ChatAnthropic
- Generate correction prompt with specific issues
- Apply corrections only to flagged sections

### 8. SaveTranslationTool

**Purpose**: 翻訳ファイルをローカルに保存

**Input Schema**:
```python
class SaveTranslationInput(BaseModel):
    original_path: str = Field(description="Original file path")
    content: str = Field(description="Translated content")
    language: str = Field(description="Target language code")
    output_root: str = Field(description="Output directory")
    naming_convention: str = Field(description="'suffix' or 'directory'")
```

**Output**: SaveResult with saved_path and success status

**Implementation**:
- Generate output path based on naming convention
- Create parent directories
- Write file content
- Update cache metadata

### 9. PushToGitHubTool

**Purpose**: 翻訳ファイルをGitHubにプッシュ

**Input Schema**:
```python
class PushToGitHubInput(BaseModel):
    repo_url: str = Field(description="GitHub repository URL")
    branch: str = Field(description="Base branch name")
    files: List[Dict] = Field(description="Files to push")
    push_option: str = Field(description="Push strategy")
    auth_token: str = Field(description="GitHub authentication token")
```

**Output**: PushResult with success status, branch_name, pr_url

**Implementation**:
- Create new branch if needed
- Push files using PyGithub
- Generate PR information

### 10. LogProgressTool

**Purpose**: 処理進捗とサマリーをログ出力

**Input Schema**:
```python
class LogProgressInput(BaseModel):
    stage: str = Field(description="Current processing stage")
    file: Optional[str] = Field(description="Current file")
    language: Optional[str] = Field(description="Current language")
    message: str = Field(description="Log message")
```

**Output**: Log confirmation

**Implementation**:
- Format log messages
- Output to console and/or file
- Track processing statistics

## Agent Configuration / Agent設定

### Agent Initialization / Agent初期化

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    max_tokens=4000
)

# Initialize tools
tools = [
    FetchGitHubFilesTool(),
    DetectFileChangesTool(),
    ParseMarkdownTool(),
    LoadGlossaryTool(),
    TranslateContentTool(llm=llm),
    ReviewTranslationTool(llm=llm),
    CorrectTranslationTool(llm=llm),
    SaveTranslationTool(),
    PushToGitHubTool(),
    LogProgressTool()
]

# Initialize memory
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# Create agent
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=translation_agent_prompt
)

# Create agent executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    max_iterations=50,
    handle_parsing_errors=True
)
```

### Agent Prompt / Agentプロンプト

```python
from langchain.prompts import PromptTemplate

translation_agent_prompt = PromptTemplate.from_template("""
You are a Translation Agent specialized in translating GitBook documentation from Japanese to multiple languages.

Your mission is to:
1. Fetch Markdown files from GitHub repository
2. Detect which files have changed since last run
3. Parse Markdown and identify protected regions (code, URLs, tags)
4. Translate Japanese text while preserving all formatting
5. Review translations for quality and correctness
6. Correct any issues found during review
7. Save translated files locally
8. Optionally push translations to GitHub

CRITICAL RULES:
- ALWAYS preserve GitBook syntax, code blocks, links, and formatting
- NEVER translate code, URLs, or technical identifiers
- ALWAYS apply glossary terms consistently
- ALWAYS review translations before saving
- If review finds BLOCKER or MAJOR issues, correct them before proceeding
- Maximum 2 correction iterations per file

You have access to the following tools:
{tools}

Use the following format:

Thought: Consider what you need to do next
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I have completed the translation task
Final Answer: Summary of translations completed

Configuration:
- Repository: {repo_url}
- Branch: {branch}
- Target Paths: {target_paths}
- Target Languages: {languages}
- Glossary: {glossary_path}
- Output Directory: {output_root}
- Push Option: {push_option}
- Naming Convention: {output_naming}

Begin!

{chat_history}
Thought: {agent_scratchpad}
""")
```

## Data Models / データモデル

### Agent State / Agent状態

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class AgentState:
    """Translation Agent の実行状態"""
    config: CLIConfig
    fetched_files: List[FetchedFile] = field(default_factory=list)
    diff_result: Optional[DiffResult] = None
    glossary: Optional[Glossary] = None
    current_file: Optional[str] = None
    current_language: Optional[str] = None
    translations_completed: int = 0
    errors: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
```

### Tool Results / ツール結果

```python
@dataclass
class ToolResult:
    """ツール実行結果の基底クラス"""
    success: bool
    message: str
    data: Optional[Dict] = None
    error: Optional[str] = None
```

## Error Handling / エラーハンドリング

### Agent Error Recovery / Agentエラー回復

Agent は以下のエラー回復戦略を使用します：

1. **Tool Execution Errors**:
   - Catch exceptions in tool execution
   - Log error with context
   - Return error observation to agent
   - Agent decides whether to retry or skip

2. **LLM API Errors**:
   - Use LangChain's built-in retry logic
   - Exponential backoff (3 retries)
   - Fallback to simpler prompts if needed

3. **GitHub API Errors**:
   - Retry with exponential backoff
   - Report rate limiting clearly
   - Continue with local operations if push fails

4. **File System Errors**:
   - Skip problematic files
   - Log errors with file paths
   - Continue processing remaining files

5. **Translation Quality Issues**:
   - Maximum 2 correction iterations
   - Proceed with best available translation after max iterations
   - Log quality issues for manual review

### Agent Guardrails / Agent ガードレール

```python
class AgentGuardrails:
    """Agent の安全な実行を保証するガードレール"""
    
    MAX_ITERATIONS = 50  # 無限ループ防止
    MAX_CORRECTION_LOOPS = 2  # 修正ループの上限
    MAX_FILE_SIZE = 1_000_000  # 1MB - 大きすぎるファイルをスキップ
    MAX_TRANSLATION_TIME = 300  # 5分 - タイムアウト
    
    @staticmethod
    def validate_tool_input(tool_name: str, input_data: Dict) -> bool:
        """ツール入力の検証"""
        # 入力データの型チェック
        # 必須フィールドの存在確認
        # 値の範囲チェック
        pass
    
    @staticmethod
    def sanitize_file_path(path: str) -> str:
        """ファイルパスのサニタイズ（ディレクトリトラバーサル防止）"""
        pass
```

## Testing Strategy / テスト戦略

### Agent Testing / Agentテスト

**Unit Tests for Tools**:
- Test each tool independently
- Mock external dependencies (GitHub API, LLM API)
- Verify tool input/output schemas

**Integration Tests for Agent**:
- Test agent with mock tools
- Verify agent reasoning flow
- Test error recovery scenarios

**End-to-End Tests**:
- Test complete translation workflow
- Use test GitHub repository
- Verify output files and quality

**Property-Based Tests**:
- Use hypothesis library
- Test translation properties (whitespace preservation, protected regions, etc.)
- Minimum 100 iterations per property

### Agent Behavior Tests / Agent動作テスト

```python
def test_agent_handles_translation_workflow():
    """Agent が翻訳ワークフローを正しく実行することを確認"""
    # Setup
    agent = create_translation_agent(config)
    
    # Execute
    result = agent.run(
        repo_url="https://github.com/test/repo",
        branch="main",
        target_paths=["docs/**/*.md"],
        languages=["en"]
    )
    
    # Verify
    assert result.success
    assert result.translations_completed > 0
    assert len(result.errors) == 0

def test_agent_recovers_from_review_failures():
    """Agent がレビュー失敗から回復することを確認"""
    # Setup with mock tools that return review failures
    agent = create_translation_agent_with_mocks(
        review_failures=2,  # First 2 reviews fail
        max_corrections=2
    )
    
    # Execute
    result = agent.run(...)
    
    # Verify agent attempted corrections
    assert result.correction_attempts == 2
    assert result.success  # Eventually succeeded or proceeded

def test_agent_respects_max_iterations():
    """Agent が最大イテレーション数を守ることを確認"""
    agent = create_translation_agent(config, max_iterations=10)
    
    # Execute with problematic input that might cause loops
    result = agent.run(...)
    
    # Verify
    assert result.iterations <= 10
```

## Performance Considerations / パフォーマンス考慮事項

### Agent Optimization / Agent最適化

1. **Tool Call Minimization**:
   - Agent should batch operations when possible
   - Cache tool results within same execution
   - Skip unnecessary tool calls based on state

2. **LLM Token Optimization**:
   - Use concise prompts
   - Limit chat history in memory
   - Chunk large files for translation

3. **Parallel Processing** (Future Enhancement):
   - Process multiple files in parallel
   - Use async tools for I/O operations
   - Parallel translation for multiple languages

## Security Considerations / セキュリティ考慮事項

1. **API Key Protection**:
   - Store in environment variables
   - Never log API keys
   - Mask in agent observations

2. **Input Validation**:
   - Validate all tool inputs
   - Sanitize file paths
   - Prevent code injection in prompts

3. **GitHub Access Control**:
   - Use minimal required permissions
   - Validate repository URLs
   - Confirm before destructive operations

## Monitoring and Observability / 監視と可観測性

### Agent Tracing / Agentトレーシング

```python
from langchain.callbacks import StdOutCallbackHandler
from langchain.callbacks.tracers import LangChainTracer

# Enable tracing
tracer = LangChainTracer()
agent_executor.run(
    ...,
    callbacks=[tracer, StdOutCallbackHandler()]
)

# Access trace data
trace = tracer.runs[-1]
print(f"Total tokens: {trace.total_tokens}")
print(f"Execution time: {trace.execution_time}")
print(f"Tool calls: {len(trace.child_runs)}")
```

### Logging / ログ出力

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gitbook-translator.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('gitbook-translator')

# Log agent actions
logger.info(f"Agent started translation for {len(files)} files")
logger.info(f"Agent completed file: {file_path}")
logger.error(f"Agent encountered error: {error}")
```

## Future Enhancements / 将来の拡張

1. **Multi-Agent System**:
   - Separate agents for fetching, translating, reviewing
   - Agent collaboration and handoff
   - Specialized agents for different document types

2. **Learning from Feedback**:
   - Store successful translations as examples
   - Fine-tune prompts based on review patterns
   - Build translation memory

3. **Advanced Planning**:
   - Use LangChain's Plan-and-Execute agent
   - Optimize translation order based on dependencies
   - Batch similar files for efficiency

4. **Human-in-the-Loop**:
   - Request human approval for critical decisions
   - Interactive correction of translations
   - Feedback collection for improvement

5. **Web Interface**:
   - Real-time agent execution monitoring
   - Interactive tool approval
   - Translation history and analytics
