"""Translation Agent using LangChain ReAct framework."""

import os
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage

from ..models import CLIConfig, AgentState
from ..tools import (
    FetchGitHubFilesTool,
    DetectFileChangesTool,
    ParseMarkdownTool,
    LoadGlossaryTool,
    TranslateContentTool,
    ReviewTranslationTool,
    CorrectTranslationTool,
    SaveTranslationTool,
    PushToGitHubTool,
    LogProgressTool,
)
from .monitoring import MetricsCollector, LangChainTracer


# Agent prompt template for ReAct framework
# Requirements: All requirements - agent orchestration
AGENT_SYSTEM_PROMPT = """You are the GitBook Translator Agent, an autonomous AI system that orchestrates the translation of GitBook-formatted Markdown documentation from Japanese to target languages while preserving all formatting, structure, and GitBook-specific syntax.

MISSION:
Your mission is to translate GitBook documentation files from a GitHub repository while maintaining perfect format preservation. You must coordinate multiple specialized tools to fetch files, detect changes, parse Markdown, translate content, review translations, correct issues, and save results.

CONFIGURATION:
- Repository: {repo_url}
- Branch: {branch}
- Target Paths: {target_paths}
- Target Languages: {languages}
- Glossary Path: {glossary_path}
- Output Root: {output_root}
- Output Naming: {output_naming}
- Push Option: {push_option}

CRITICAL RULES:
1. FORMAT PRESERVATION IS PARAMOUNT: All GitBook syntax, line breaks, indentation, spacing, code blocks, tags, links, and structure MUST be preserved exactly.
2. TRANSLATE ONLY JAPANESE TEXT: Only translate text containing Japanese characters. Leave all other content unchanged.
3. PROTECT SPECIAL REGIONS: Never translate code blocks, inline code, URLs, GitBook tags, HTML tags, YAML frontmatter, or template expressions.
4. APPLY GLOSSARY CONSISTENTLY: Use exact terminology from the glossary without variation.
5. PROCESS EFFICIENTLY: Use diff detection to skip unchanged files and minimize LLM token consumption.
6. ITERATE FOR QUALITY: Review all translations and correct issues up to 2 times before proceeding.
7. ISOLATE ERRORS: If one file or language fails, continue processing others.
8. LOG EVERYTHING: Log progress, errors, and issues at every stage for transparency.

WORKFLOW:
1. Fetch files from GitHub repository using FetchGitHubFilesTool
2. Detect changes since last run using DetectFileChangesTool (skip unchanged files)
3. Load glossary using LoadGlossaryTool
4. For each changed file and each target language:
   a. Log progress using LogProgressTool
   b. Parse Markdown using ParseMarkdownTool (identify protected regions)
   c. Translate content using TranslateContentTool (apply glossary, preserve format)
   d. Review translation using ReviewTranslationTool (verify quality and completeness)
   e. If BLOCKER or MAJOR issues found (max 2 iterations):
      - Correct translation using CorrectTranslationTool
      - Review again using ReviewTranslationTool
   f. Save translation using SaveTranslationTool
5. Optionally push to GitHub using PushToGitHubTool (based on push_option)
6. Log final summary using LogProgressTool

GUARDRAILS:
- Maximum iterations: 50 actions (hard limit)
- Maximum correction loops per file: 2 (enforced by system)
- File size limit: 1MB per file (files exceeding this will be skipped)
- Translation timeout: 5 minutes per file (enforced by LLM timeout)
- Input validation: All paths and parameters are validated and sanitized
- Path sanitization: Path traversal attempts are blocked
- Sensitive data masking: API keys and tokens are masked in all logs
- Never expose API keys or tokens in logs or outputs

IMPORTANT:
- Always think step-by-step before taking action
- Use tools one at a time and wait for observations
- If a tool fails, analyze the error and adjust your approach
- Track which files and languages have been processed
- Ensure all target languages are processed for each file
- Provide clear final summary when complete"""


class TranslationAgent:
    """LangChain ReAct Agent for orchestrating GitBook translation workflow."""

    # Guardrail constants
    # Requirements: All requirements - safety
    MAX_ITERATIONS = 50  # Maximum agent iterations
    MAX_CORRECTION_LOOPS = 2  # Maximum correction loops per file
    MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1MB file size limit
    TRANSLATION_TIMEOUT_SECONDS = 300  # 5 minutes per file
    
    def __init__(self, config: CLIConfig, llm: Optional[ChatOpenAI] = None):
        """Initialize the Translation Agent.

        Args:
            config: CLI configuration
            llm: LangChain LLM instance (defaults to ChatOpenAI)
        """
        # Validate and sanitize configuration
        # Requirements: All requirements - safety
        self._validate_config(config)
        
        self.config = config
        self.state = AgentState(config=config)
        
        # Track correction loops per file
        # Requirements: All requirements - safety
        self.correction_loops: Dict[str, int] = {}
        
        # Initialize monitoring and observability
        # Requirements: 16.2, 16.4
        self.metrics_collector = MetricsCollector()
        self.tracer = LangChainTracer(self.metrics_collector)
        
        # Initialize LLM (ChatOpenAI or ChatAnthropic)
        # Requirements: All requirements - agent setup
        self.llm = llm or ChatOpenAI(
            temperature=0,
            model="gpt-4",
            request_timeout=self.TRANSLATION_TIMEOUT_SECONDS
        )

        # Initialize all 10 tools
        # Requirements: All requirements - agent setup
        self.tools: List[BaseTool] = [
            FetchGitHubFilesTool(),
            DetectFileChangesTool(),
            ParseMarkdownTool(),
            LoadGlossaryTool(),
            TranslateContentTool(),
            ReviewTranslationTool(),
            CorrectTranslationTool(),
            SaveTranslationTool(),
            PushToGitHubTool(),
            LogProgressTool(),
        ]

        # Create system prompt with configuration
        # Requirements: All requirements - agent orchestration
        system_prompt = AGENT_SYSTEM_PROMPT.format(
            repo_url=config.repo_url,
            branch=config.branch,
            target_paths=str(config.target_paths),
            languages=str(config.languages),
            glossary_path=config.glossary_path,
            output_root=config.output_root,
            output_naming=config.output_naming,
            push_option=config.push_option,
        )
        
        # Create prompt template for ReAct agent
        # Requirements: All requirements - agent setup
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Initialize conversation memory (message history)
        # Requirements: All requirements - agent setup
        # Note: langgraph manages state internally, but we maintain a message history
        # for compatibility with the ConversationBufferMemory concept
        self.memory: List[Dict[str, Any]] = []
        
        # Create ReAct agent with create_react_agent (using langgraph)
        # Requirements: All requirements - agent setup
        # langgraph's create_react_agent returns a compiled graph
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=system_prompt,  # System prompt to guide the agent
        )
        
        # Create AgentExecutor (the compiled graph acts as the executor)
        # Requirements: All requirements - agent setup
        # Configure with error handling and guardrails
        self.agent_executor = self.agent
        self.max_iterations = self.MAX_ITERATIONS
        self.handle_parsing_errors = True  # Handle parsing errors gracefully

    def _validate_config(self, config: CLIConfig) -> None:
        """Validate and sanitize configuration parameters.
        
        Args:
            config: CLI configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Requirements: All requirements - safety
        
        # Validate repo_url format
        if not config.repo_url:
            raise ValueError("repo_url must be non-empty")
        
        # Basic GitHub URL validation
        github_pattern = r"^https?://github\.com/[\w\-]+/[\w\-]+/?$"
        if not re.match(github_pattern, config.repo_url.rstrip("/")):
            raise ValueError(
                f"Invalid GitHub repository URL: {config.repo_url}. "
                "Expected format: https://github.com/owner/repo"
            )
        
        # Validate branch name (no path traversal)
        if not config.branch or ".." in config.branch or "/" in config.branch:
            raise ValueError(
                f"Invalid branch name: {config.branch}. "
                "Branch name must not contain '..' or '/'"
            )
        
        # Validate target_paths (sanitize for path traversal)
        if not config.target_paths:
            raise ValueError("target_paths must contain at least one pattern")
        
        for path in config.target_paths:
            if ".." in path:
                raise ValueError(
                    f"Invalid target path: {path}. "
                    "Path must not contain '..'"
                )
        
        # Validate languages (basic format check)
        if not config.languages:
            raise ValueError("languages must contain at least one language code")
        
        valid_lang_pattern = r"^[a-z]{2}(-[A-Z]{2})?$"
        for lang in config.languages:
            if not re.match(valid_lang_pattern, lang):
                raise ValueError(
                    f"Invalid language code: {lang}. "
                    "Expected format: 'en', 'zh-CN', 'zh-TW', etc."
                )
        
        # Validate glossary_path (sanitize for path traversal)
        if not config.glossary_path:
            raise ValueError("glossary_path must be non-empty")
        
        glossary_path = Path(config.glossary_path)
        if ".." in glossary_path.parts:
            raise ValueError(
                f"Invalid glossary path: {config.glossary_path}. "
                "Path must not contain '..'"
            )
        
        # Validate output_root (sanitize for path traversal)
        if not config.output_root:
            raise ValueError("output_root must be non-empty")
        
        output_root = Path(config.output_root)
        if ".." in output_root.parts:
            raise ValueError(
                f"Invalid output root: {config.output_root}. "
                "Path must not contain '..'"
            )
        
        # Validate push_option
        valid_push_options = ["none", "push_same_repo_direct", "push_same_repo_new_branch"]
        if config.push_option not in valid_push_options:
            raise ValueError(
                f"Invalid push_option: {config.push_option}. "
                f"Must be one of: {valid_push_options}"
            )
        
        # Validate output_naming
        valid_naming_options = ["suffix", "directory"]
        if config.output_naming not in valid_naming_options:
            raise ValueError(
                f"Invalid output_naming: {config.output_naming}. "
                f"Must be one of: {valid_naming_options}"
            )

    def _sanitize_path(self, path: str) -> str:
        """Sanitize a file path to prevent path traversal attacks.
        
        Args:
            path: Path to sanitize
            
        Returns:
            Sanitized path
            
        Raises:
            ValueError: If path contains dangerous patterns
        """
        # Requirements: All requirements - safety
        
        # Check for absolute paths first (before converting to Path object)
        # On Windows, check for drive letters (C:, D:, etc.) and UNC paths (\\)
        # On Unix, check for paths starting with /
        if (path.startswith('/') or 
            path.startswith('\\') or 
            (len(path) >= 2 and path[1] == ':')):
            raise ValueError(f"Absolute paths not allowed: {path}")
        
        # Check for path traversal attempts
        if ".." in Path(path).parts:
            raise ValueError(f"Path traversal detected in: {path}")
        
        # Convert to Path object for normalization
        normalized = Path(path).resolve()
        
        return str(normalized)

    def _validate_file_size(self, content: str, file_path: str) -> None:
        """Validate that file size is within limits.
        
        Args:
            content: File content
            file_path: Path to file (for error messages)
            
        Raises:
            ValueError: If file exceeds size limit
        """
        # Requirements: All requirements - safety
        
        file_size = len(content.encode("utf-8"))
        if file_size > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File {file_path} exceeds size limit: "
                f"{file_size} bytes > {self.MAX_FILE_SIZE_BYTES} bytes (1MB)"
            )

    def _check_correction_limit(self, file_path: str) -> bool:
        """Check if correction loop limit has been reached for a file.
        
        Args:
            file_path: Path to file being corrected
            
        Returns:
            True if correction is allowed, False if limit reached
        """
        # Requirements: All requirements - safety
        
        current_loops = self.correction_loops.get(file_path, 0)
        return current_loops < self.MAX_CORRECTION_LOOPS

    def _increment_correction_loop(self, file_path: str) -> None:
        """Increment correction loop counter for a file.
        
        Args:
            file_path: Path to file being corrected
        """
        # Requirements: All requirements - safety
        
        current_loops = self.correction_loops.get(file_path, 0)
        self.correction_loops[file_path] = current_loops + 1

    def _mask_sensitive_info(self, text: str) -> str:
        """Mask sensitive information in logs and outputs.
        
        Args:
            text: Text that may contain sensitive information
            
        Returns:
            Text with sensitive information masked
        """
        # Requirements: All requirements - safety
        
        # Mask API keys and tokens
        # Pattern: any string that looks like an API key or token
        patterns = [
            (r"ghp_[a-zA-Z0-9]{30,}", "***GITHUB_TOKEN***"),  # GitHub tokens (at least 30 chars after prefix)
            (r"sk-[a-zA-Z0-9]{40,}", "***OPENAI_KEY***"),  # OpenAI keys (at least 40 chars after prefix)
            (r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", "Bearer ***TOKEN***"),  # Bearer tokens
            (r"token[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9\-._~+/]+)", r"token: ***TOKEN***"),  # Generic tokens
        ]
        
        masked_text = text
        for pattern, replacement in patterns:
            masked_text = re.sub(pattern, replacement, masked_text, flags=re.IGNORECASE)
        
        return masked_text

    def run(self) -> Dict[str, Any]:
        """Execute the translation workflow with guardrails.
        
        This method implements the complete agent execution flow:
        1. Initialize agent state
        2. Run agent with configuration
        3. Handle agent errors and retries
        4. Collect execution results
        
        Requirements: All requirements - execution

        Returns:
            Dictionary with execution results including:
            - status: "success" or "error"
            - output: Final agent output message
            - messages: All conversation messages
            - intermediate_steps: List of tool calls made
            - correction_loops: Correction loop counts per file
            - state: Final agent state
            - errors: List of errors encountered (if any)
            - metrics: Execution metrics including timing and token usage
        """
        import time
        from datetime import datetime
        
        # Initialize agent state
        # Requirements: All requirements - execution
        start_time = time.time()
        self.state = AgentState(config=self.config)
        execution_errors = []
        retry_count = 0
        max_retries = 3
        
        # Record agent start in tracer
        # Requirements: 16.2, 16.4
        self.tracer.record_agent_start(
            agent_name="GitBook Translator Agent",
            input_text=f"Translate {self.config.repo_url} to {self.config.languages}"
        )
        
        try:
            # Construct the input question for the agent
            # Requirements: All requirements - execution
            input_question = (
                f"Translate GitBook documentation from repository {self.config.repo_url} "
                f"(branch: {self.config.branch}) to languages {self.config.languages}. "
                f"Process files matching patterns {self.config.target_paths}. "
                f"Use glossary at {self.config.glossary_path}. "
                f"Save output to {self.config.output_root} with {self.config.output_naming} naming. "
                f"Push option: {self.config.push_option}."
            )
            
            # Run agent with configuration and retry logic
            # Requirements: All requirements - execution
            result = None
            last_error = None
            
            while retry_count <= max_retries:
                try:
                    # Create message for the agent
                    messages = [HumanMessage(content=input_question)]
                    
                    # Execute the agent (langgraph agents use messages format)
                    # The agent will iterate up to max_iterations times
                    # Requirements: All requirements - safety (max iterations guardrail)
                    result = self.agent_executor.invoke(
                        {"messages": messages},
                        config={"recursion_limit": self.max_iterations}
                    )
                    
                    # If we get here, execution succeeded
                    break
                    
                except Exception as e:
                    # Handle agent errors and retries
                    # Requirements: All requirements - execution
                    last_error = e
                    retry_count += 1
                    
                    # Mask sensitive information in error
                    masked_error = self._mask_sensitive_info(str(e))
                    
                    # Log the error
                    error_info = {
                        "attempt": retry_count,
                        "error": masked_error,
                        "timestamp": datetime.now().isoformat(),
                    }
                    execution_errors.append(error_info)
                    
                    # Record error in metrics
                    # Requirements: 16.2, 16.4
                    self.metrics_collector.record_error(
                        error_type=type(e).__name__,
                        error_message=masked_error,
                        context={"attempt": retry_count}
                    )
                    
                    # If we've exhausted retries, re-raise
                    if retry_count > max_retries:
                        raise
                    
                    # Wait before retrying (exponential backoff)
                    wait_time = 2 ** retry_count  # 2, 4, 8 seconds
                    time.sleep(wait_time)
            
            # Collect execution results
            # Requirements: All requirements - execution
            
            # Store conversation in memory (mask sensitive info)
            # Requirements: All requirements - safety
            self.memory.append({
                "input": self._mask_sensitive_info(input_question),
                "output": result.get("messages", []) if result else [],
                "timestamp": datetime.now().isoformat(),
            })
            
            # Extract the final message from the result
            result_messages = result.get("messages", []) if result else []
            final_output = result_messages[-1].content if result_messages else "No output"
            
            # Mask sensitive information in final output
            # Requirements: All requirements - safety
            final_output = self._mask_sensitive_info(final_output)
            
            # Record agent end in tracer
            # Requirements: 16.2, 16.4
            self.tracer.record_agent_end(output_text=final_output, success=True)
            
            # Extract intermediate steps (tool calls)
            # Requirements: All requirements - execution
            intermediate_steps = []
            tool_call_count = {}
            
            for msg in result_messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.get("name", "unknown")
                        tool_call_count[tool_name] = tool_call_count.get(tool_name, 0) + 1
                        
                        intermediate_steps.append({
                            "tool": tool_name,
                            "input": self._mask_sensitive_info(str(tool_call.get("args", {}))),
                            "timestamp": datetime.now().isoformat(),
                        })
            
            # Calculate execution duration
            execution_duration = time.time() - start_time
            
            # Complete metrics collection
            # Requirements: 16.2, 16.4
            final_metrics = self.metrics_collector.complete()
            
            # Collect final state information
            # Requirements: All requirements - execution
            final_state = {
                "fetched_files_count": len(self.state.fetched_files),
                "current_file": self.state.current_file,
                "current_language": self.state.current_language,
                "results_count": sum(len(langs) for langs in self.state.results.values()),
                "errors_count": len(self.state.errors),
            }
            
            # Build comprehensive result dictionary
            # Requirements: All requirements - execution
            return {
                "status": "success",
                "output": final_output,
                "messages": result_messages,
                "intermediate_steps": intermediate_steps,
                "tool_call_count": tool_call_count,
                "correction_loops": dict(self.correction_loops),
                "state": final_state,
                "execution_duration": execution_duration,
                "retry_count": retry_count,
                "errors": execution_errors if execution_errors else None,
                "timestamp": datetime.now().isoformat(),
                "metrics": final_metrics.to_dict(),
                "reasoning_trace": self.tracer.get_reasoning_steps(),
            }
            
        except Exception as e:
            # Handle agent errors
            # Requirements: All requirements - execution
            
            # Calculate execution duration
            execution_duration = time.time() - start_time
            
            # Mask sensitive information in error messages
            # Requirements: All requirements - safety
            error_message = self._mask_sensitive_info(str(e))
            
            # Record agent end in tracer with error
            # Requirements: 16.2, 16.4
            self.tracer.record_agent_end(output_text=error_message, success=False)
            
            # Collect error details
            error_details = {
                "error_type": type(e).__name__,
                "error_message": error_message,
                "retry_count": retry_count,
                "execution_duration": execution_duration,
                "timestamp": datetime.now().isoformat(),
            }
            
            # Add to execution errors list
            execution_errors.append(error_details)
            
            # Complete metrics collection
            # Requirements: 16.2, 16.4
            final_metrics = self.metrics_collector.complete()
            
            # Collect partial state information if available
            # Requirements: All requirements - execution
            partial_state = None
            try:
                partial_state = {
                    "fetched_files_count": len(self.state.fetched_files) if self.state else 0,
                    "current_file": self.state.current_file if self.state else None,
                    "current_language": self.state.current_language if self.state else None,
                    "results_count": sum(len(langs) for langs in self.state.results.values()) if self.state else 0,
                    "errors_count": len(self.state.errors) if self.state else 0,
                }
            except Exception:
                # If we can't collect state, just skip it
                pass
            
            return {
                "status": "error",
                "error": error_message,
                "error_type": type(e).__name__,
                "message": f"Agent execution failed: {error_message}",
                "errors": execution_errors,
                "retry_count": retry_count,
                "execution_duration": execution_duration,
                "state": partial_state,
                "timestamp": datetime.now().isoformat(),
                "metrics": final_metrics.to_dict(),
                "reasoning_trace": self.tracer.get_reasoning_steps(),
            }
