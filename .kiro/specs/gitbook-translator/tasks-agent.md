# AI Agent Implementation Plan / AI Agent実装計画

## Overview / 概要

このタスクリストは、LangChain ReAct Agentを使用したGitBook Translatorの実装計画です。Translation Agentが10個のカスタムツールを使用して、自律的に翻訳ワークフローを実行します。

## Implementation Tasks / 実装タスク

- [x] 1. Set up project structure and LangChain Agent framework
  - Create Python project with necessary dependencies
  - Install langchain, langchain-openai, langchain-community, PyGithub, hypothesis, pytest
  - Define project structure: src/agent/, src/tools/, src/models/, tests/
  - Set up configuration management (environment variables, config files)
  - Create requirements.txt with all dependencies
  - _Requirements: All requirements - foundational setup_

- [x] 2. Implement core data models and interfaces
  - Create dataclasses for CLIConfig, FetchedFile, FileMetadata, DiffResult
  - Create dataclasses for Segment, SegmentMetadata, ParsedMarkdown, StructureInfo
  - Create dataclasses for Glossary, TranslationRequest, TranslationResult
  - Create dataclasses for Issue, ReviewRequest, ReviewResult
  - Create dataclasses for AgentState, ToolResult
  - Create enums for SegmentType, IssueSeverity, IssueCategory
  - _Requirements: All requirements - data structures_

- [x] 3. Implement FetchGitHubFilesTool

  - [x] 3.1 Create BaseTool subclass for GitHub file fetching
    - Define tool name, description, and args_schema
    - Implement _run method with PyGithub integration
    - Support GITHUB_TOKEN environment variable
    - _Requirements: 1.1, 1.5_

  - [x] 3.2 Implement glob pattern resolution
    - Resolve glob patterns using fnmatch
    - Fetch file content and metadata (commit hash, last modified)
    - Return List[FetchedFile] as tool output
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 3.3 Add error handling and rate limiting
    - Handle authentication failures
    - Handle repository not found errors
    - Implement exponential backoff for rate limiting
    - Handle network errors with retry logic (max 3 attempts)
    - _Requirements: 1.4, 16.1_

  - [x] 3.4 Write unit tests for FetchGitHubFilesTool
    - Test with mock GitHub API
    - Test glob pattern resolution
    - Test error handling scenarios
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 4. Implement DetectFileChangesTool

  - [x] 4.1 Create BaseTool subclass for diff detection
    - Define tool name, description, and args_schema
    - Implement _run method for change detection
    - _Requirements: 2.1, 2.2_

  - [x] 4.2 Implement cache management
    - Load cache from .gitbook-translator-cache.json
    - Compare commit hashes between current and cached files
    - Categorize files as new, modified, or unchanged
    - Save updated cache after processing
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 4.3 Write property test for diff detection
    - **Property 14: Diff detection accuracy**
    - **Validates: Requirements 2.3, 2.4**

  - [x] 4.4 Write unit tests for DetectFileChangesTool
    - Test first run (all files new)
    - Test subsequent runs with changes
    - Test cache persistence
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5. Implement ParseMarkdownTool
  - [x] 5.1 Create BaseTool subclass for Markdown parsing
    - Define tool name, description, and args_schema
    - Implement _run method for parsing
    - _Requirements: 3.1, 4.3, 4.4_

  - [x] 5.2 Implement protected region detection
    - Detect YAML frontmatter (--- to ---)
    - Detect fenced code blocks (``` to ```)
    - Detect inline code (`...`)
    - Detect GitBook tags ({% ... %}, {{ ... }})
    - Detect HTML tags and attributes
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 4.1, 4.2_

  - [x] 5.3 Implement link and image path protection
    - Parse Markdown links [text](URL) and protect URL
    - Parse image references ![alt](path) and protect path
    - Detect and protect relative paths, anchors, file references
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 5.4 Capture structure information
    - Record line breaks, indentation, and whitespace patterns
    - Store in StructureInfo for reconstruction
    - _Requirements: 3.1_

  - [x] 5.5 Write property test for protected region detection
    - **Property 2: Protected region round-trip**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.5**

  - [x] 5.6 Write property test for link URL preservation
    - **Property 3: Link URL preservation**
    - **Validates: Requirements 5.1**

  - [x] 5.7 Write property test for image path preservation
    - **Property 4: Image path preservation**
    - **Validates: Requirements 5.2**

  - [x] 5.8 Write property test for relative path preservation
    - **Property 5: Relative path preservation**
    - **Validates: Requirements 5.3, 5.4, 5.5**

- [x] 6. Implement LoadGlossaryTool


  - [x] 6.1 Create BaseTool subclass for glossary loading
    - Define tool name, description, and args_schema
    - Implement _run method for loading and parsing
    - _Requirements: 8.1_

  - [x] 6.2 Implement glossary format detection
    - Auto-detect JSON/CSV format
    - Parse into Glossary dataclass with term mappings
    - Support multiple language mappings
    - _Requirements: 8.1, 8.2_

  - [x] 6.3 Write property test for glossary term consistency
    - **Property 10: Glossary term consistency**
    - **Validates: Requirements 8.3, 8.4**

  - [x] 6.4 Write property test for multi-language glossary application
    - **Property 17: Multi-language glossary application**
    - **Validates: Requirements 15.2**

  - [x] 6.5 Write unit tests for LoadGlossaryTool
    - Test JSON format parsing
    - Test CSV format parsing
    - Test format auto-detection
    - _Requirements: 8.1, 8.2_

- [ ] 7. Implement TranslateContentTool
  - [x] 7.1 Create BaseTool subclass for translation
    - Define tool name, description, and args_schema
    - Initialize LangChain ChatOpenAI/ChatAnthropic
    - Configure API authentication from environment variables
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 7.2 Build translation prompt template with LangChain
    - Create ChatPromptTemplate with format preservation rules
    - Include glossary terms in prompt
    - Include structure information
    - Emphasize formal, business-appropriate tone
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 7.3 Implement _run method for translation
    - Send segments and structure to LLM via LangChain
    - Parse LLM response into translated segments
    - Reconstruct full content with protected regions
    - Validate output structure matches input
    - _Requirements: 9.5_

  - [x] 7.4 Add retry logic and error handling
    - Use LangChain's built-in retry mechanisms
    - Handle timeout errors
    - Handle invalid response format
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 7.5 Write property test for Japanese-only translation
    - **Property 8: Japanese-only translation**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

  - [x] 7.6 Write property test for technical term preservation
    - **Property 11: Technical term preservation**
    - **Validates: Requirements 8.5**

  - [x] 7.7 Write unit tests for TranslateContentTool
    - Test with mock LLM responses
    - Test glossary application
    - Test protected region preservation
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 8. Implement ReviewTranslationTool
  - [x] 8.1 Create BaseTool subclass for review
    - Define tool name, description, and args_schema
    - Initialize LangChain ChatOpenAI/ChatAnthropic
    - _Requirements: 10.1_

  - [x] 8.2 Build review prompt template with LangChain
    - Create ChatPromptTemplate with verification checklist
    - Include original and translated content
    - Include glossary for term verification
    - Use PydanticOutputParser for structured JSON output
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [x] 8.3 Implement _run method for review
    - Send review request to LLM via LangChain
    - Parse JSON response into List[Issue] using Pydantic
    - Classify issues by severity (BLOCKER, MAJOR, MINOR)
    - Determine if translation is approved
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 8.4 Add issue classification logic
    - Classify structural damage, link corruption as BLOCKER
    - Classify semantic errors, glossary violations as MAJOR
    - Classify stylistic improvements as MINOR
    - _Requirements: 11.2, 11.3, 11.4, 11.5_

  - [x] 8.5 Write property test for complete translation verification
    - **Property 13: Complete translation**
    - **Validates: Requirements 10.2**

  - [x] 8.6 Write unit tests for ReviewTranslationTool
    - Test with mock LLM responses
    - Test issue classification
    - Test approval logic
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 9. Implement CorrectTranslationTool
  - [x] 9.1 Create BaseTool subclass for correction
    - Define tool name, description, and args_schema
    - Initialize LangChain ChatOpenAI/ChatAnthropic
    - _Requirements: 12.1, 12.2_

  - [x] 9.2 Build correction prompt template
    - Create prompt that focuses on specific issues
    - Include issue descriptions and suggestions
    - Emphasize minimal changes to non-problematic sections
    - _Requirements: 12.2_

  - [x] 9.3 Implement _run method for correction
    - Send correction request to LLM
    - Parse corrected content
    - Validate corrections address the issues
    - _Requirements: 12.2, 12.3_


  - [x] 9.4 Write property test for whitespace preservation
    - **Property 1: Whitespace preservation**
    - **Validates: Requirements 3.1**

  - [x] 9.5 Write property test for table structure preservation
    - **Property 6: Table structure preservation**
    - **Validates: Requirements 6.1, 6.3, 6.4**

  - [x] 9.6 Write property test for table cell translation
    - **Property 7: Table cell translation**
    - **Validates: Requirements 6.2**

  - [x] 9.7 Write property test for punctuation preservation
    - **Property 9: Punctuation preservation**
    - **Validates: Requirements 7.5**

  - [x] 9.8 Write property test for Markdown validity preservation
    - **Property 12: Markdown validity preservation**
    - **Validates: Requirements 9.5**

  - [x] 9.9 Write unit tests for CorrectTranslationTool
    - Test with various issue types
    - Test correction application
    - _Requirements: 12.1, 12.2, 12.3_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement SaveTranslationTool
  - [x] 11.1 Create BaseTool subclass for file saving
    - Define tool name, description, and args_schema
    - Implement _run method for saving
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

  - [x] 11.2 Implement output path generation logic
    - Implement suffix naming: <name>.<lang>.md
    - Implement directory naming: /<lang>/<original-path>
    - Preserve relative directory structure
    - _Requirements: 13.1, 13.2, 13.4_

  - [x] 11.3 Implement file saving with directory creation
    - Create parent directories automatically using pathlib
    - Write translated content to file
    - Handle file write errors gracefully
    - Update cache metadata after successful save
    - _Requirements: 13.3, 13.5_

  - [x] 11.4 Write property test for file naming consistency
    - **Property 15: File naming consistency**
    - **Validates: Requirements 13.1, 13.2**

  - [x] 11.5 Write property test for directory structure preservation
    - **Property 16: Directory structure preservation**
    - **Validates: Requirements 13.4**

  - [x] 11.6 Write unit tests for SaveTranslationTool
    - Test suffix naming mode
    - Test directory naming mode
    - Test directory creation
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [x] 12. Implement PushToGitHubTool
  - [x] 12.1 Create BaseTool subclass for GitHub push
    - Define tool name, description, and args_schema
    - Implement _run method for pushing
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [x] 12.2 Implement branch creation logic
    - Generate branch name: translation/<lang>/<timestamp>
    - Use PyGithub API to create new branch
    - _Requirements: 14.3_

  - [x] 12.3 Implement file push operations
    - Push translated files to GitHub using PyGithub
    - Handle push_same_repo_direct with user confirmation
    - Handle push_same_repo_new_branch automatically
    - _Requirements: 14.2, 14.3, 14.4_

  - [x] 12.4 Add error handling for GitHub push
    - Report push errors clearly
    - Ensure local files are saved even if push fails
    - _Requirements: 14.5_

  - [x] 12.5 Generate PR information
    - Provide branch name and PR creation instructions
    - _Requirements: 14.4_

  - [x] 12.6 Write unit tests for PushToGitHubTool
    - Test with mock GitHub API
    - Test branch creation
    - Test file push
    - Test error handling
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 13. Implement LogProgressTool
  - [x] 13.1 Create BaseTool subclass for logging
    - Define tool name, description, and args_schema
    - Implement _run method for logging
    - _Requirements: 16.1, 16.2, 16.3, 16.4_

  - [x] 13.2 Implement progress logging
    - Log current file, language, and processing stage
    - Format log messages clearly
    - _Requirements: 16.2_

  - [x] 13.3 Implement error logging with context
    - Log errors with file path, language, operation
    - Mask sensitive information (API keys, tokens)
    - _Requirements: 16.1_

  - [x] 13.4 Implement issue logging
    - Log all Reviewer AI issues with severity and location
    - _Requirements: 16.3_

  - [x] 13.5 Implement summary reporting
    - Generate summary with files processed, translations created, errors
    - Include processing duration
    - _Requirements: 16.4_

  - [x] 13.6 Write property test for log completeness
    - **Property 19: Log completeness**
    - **Validates: Requirements 16.1**

  - [x] 13.7 Write property test for progress logging
    - **Property 20: Progress logging**
    - **Validates: Requirements 16.2**

  - [x] 13.8 Write unit tests for LogProgressTool
    - Test log formatting
    - Test error logging
    - Test summary generation
    - _Requirements: 16.1, 16.2, 16.3, 16.4_

- [x] 14. Implement Translation Agent
  - [x] 14.1 Create agent prompt template
    - Define agent mission and rules
    - Include configuration parameters
    - Define Thought/Action/Observation format
    - _Requirements: All requirements - agent orchestration_

  - [x] 14.2 Initialize LangChain ReAct Agent
    - Initialize ChatOpenAI/ChatAnthropic LLM
    - Create tool list with all 10 tools
    - Initialize ConversationBufferMemory
    - Create ReAct agent with create_react_agent
    - Create AgentExecutor with error handling
    - _Requirements: All requirements - agent setup_

  - [x] 14.3 Implement agent guardrails
    - Set max_iterations limit (50)
    - Implement max correction loops (2)
    - Add file size limits
    - Add translation timeout
    - Implement input validation
    - Implement path sanitization
    - _Requirements: All requirements - safety_

  - [x] 14.4 Implement agent execution flow
    - Initialize agent state
    - Run agent with configuration
    - Handle agent errors and retries
    - Collect execution results
    - _Requirements: All requirements - execution_

  - [x] 14.5 Write property test for error isolation
    - **Property 18: Error isolation**
    - **Validates: Requirements 15.4**

  - [x] 14.6 Write integration tests for agent
    - Test complete translation workflow
    - Test with mock tools
    - Test error recovery
    - Test multi-language processing
    - _Requirements: All requirements - integration_

- [x] 15. Implement CLI interface
  - [x] 15.1 Create CLI parameter parser
    - Use argparse or click for CLI
    - Define all parameters (repo_url, branch, target_paths, etc.)
    - Add help text and usage examples
    - _Requirements: All requirements - user interface_

  - [x] 15.2 Implement configuration validation
    - Validate repo_url format
    - Validate branch name
    - Validate target_paths patterns
    - Validate language codes
    - Validate glossary_path existence
    - Validate output_root path
    - _Requirements: 16.1, 16.5_

  - [x] 15.3 Create main entry point
    - Parse CLI arguments
    - Validate configuration
    - Initialize and run Translation Agent
    - Handle process exit codes
    - _Requirements: All requirements - entry point_


  - [x] 15.4 Write unit tests for CLI
    - Test argument parsing
    - Test validation logic
    - Test error messages
    - _Requirements: 16.1, 16.5_

- [ ] 16. Create documentation and examples
  - [x] 16.1 Write README with usage instructions
    - Document all CLI parameters
    - Provide example commands
    - Explain glossary format
    - Include troubleshooting guide
    - Document LangChain configuration and API key setup
    - Document agent behavior and tool usage
    - _Requirements: 16.5_


  - [x] 16.2 Create example glossary file
    - Provide sample glossary JSON
    - Document glossary format options
    - Include examples for multiple languages
    - _Requirements: 8.1, 8.2_


  - [x] 16.3 Create example configuration files
    - Provide .env.example with API keys
    - Provide config.yaml.example
    - Document all configuration options
    - _Requirements: All requirements - configuration_


  - [x] 16.4 Write agent usage guide

    - Explain agent reasoning process
    - Document tool descriptions and usage
    - Provide troubleshooting for agent issues
    - Include examples of agent execution logs
    - _Requirements: All requirements - documentation_

- [x] 17. Implement monitoring and observability
  - [x] 17.1 Add LangChain tracing
    - Configure LangChainTracer
    - Enable callback handlers
    - Log agent reasoning steps
    - Track token usage
    - _Requirements: 16.2, 16.4_

  - [x] 17.2 Add execution metrics
    - Track execution time per file
    - Track tool call counts
    - Track LLM API costs
    - Generate performance reports
    - _Requirements: 16.4_

  - [x] 17.3 Write unit tests for monitoring
    - Test tracer integration
    - Test metrics collection
    - _Requirements: 16.2, 16.4_

- [x] 18. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 19. End-to-end testing and validation
  - [x] 19.1 Create test repository
    - Set up test GitHub repository
    - Add sample GitBook documentation
    - Include various Markdown features
    - _Requirements: All requirements - testing_


  - [x] 19.2 Run end-to-end tests
    - Test complete translation workflow
    - Test with multiple languages
    - Test error scenarios
    - Test GitHub push operations
    - _Requirements: All requirements - validation_

  - [x] 19.3 Validate translation quality
    - Review translated outputs
    - Verify format preservation
    - Verify glossary application
    - Verify link and image preservation
    - _Requirements: All requirements - quality_

  - [x] 19.4 Performance testing
    - Test with large repositories
    - Measure execution time
    - Measure token usage
    - Identify bottlenecks
    - _Requirements: All requirements - performance_

## Notes / 注意事項

- Each tool should be implemented as a LangChain BaseTool subclass
- All tools should have clear descriptions for the agent to understand
- Property-based tests should use hypothesis with @settings(max_examples=100)
- Integration tests should use mock services to avoid external dependencies
- Agent should be tested with various scenarios to ensure robust behavior
- Documentation should include agent reasoning examples and troubleshooting
