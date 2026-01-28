# Implementation Plan / 実装計画

- [ ] 1. Set up project structure and core interfaces
  - Create Python project with necessary dependencies (langchain, hypothesis, pytest, PyGithub)
  - Define core dataclasses and interfaces for all major components
  - Set up testing framework (pytest and hypothesis for property-based testing)
  - Configure project structure with pyproject.toml or setup.py
  - Create requirements.txt with langchain, langchain-openai, PyGithub, hypothesis, pytest
  - _Requirements: All requirements - foundational setup_

- [ ] 2. Implement CLI interface and configuration validation
  - Create CLI parameter parser using argparse or click
  - Implement CLIConfig dataclass validation
  - Add validation for repo_url, branch, target_paths, languages
  - Add validation for glossary_path, output_root, push_option, output_naming
  - Provide clear error messages for invalid configurations
  - _Requirements: 16.1, 16.5_

- [ ] 3. Implement GitHub Fetcher component
  - [ ] 3.1 Create GitHub API client with authentication support
    - Implement GitHub API client using PyGithub
    - Support GITHUB_TOKEN environment variable
    - Handle API rate limiting with exponential backoff
    - _Requirements: 1.1, 1.5_

  - [ ] 3.2 Implement file fetching with glob pattern resolution
    - Resolve glob patterns using fnmatch or pathlib
    - Fetch file content and metadata (commit hash, last modified)
    - Return List[FetchedFile]
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ] 3.3 Add error handling for GitHub operations
    - Handle authentication failures
    - Handle repository not found errors
    - Handle network errors with retry logic (max 3 attempts)
    - _Requirements: 1.4, 16.1_

- [ ] 4. Implement Cache Manager and Diff Detection
  - [ ] 4.1 Create cache file structure and I/O operations
    - Define FileMetadata and cache JSON structure
    - Implement loadCache and saveCache functions
    - Store cache in .gitbook-translator-cache.json
    - _Requirements: 2.1_
  
  - [ ] 4.2 Implement diff detection logic
    - Compare commit hashes between current and cached files
    - Classify files as new, modified, or unchanged
    - Return DiffResult with categorized files
    - _Requirements: 2.2, 2.3, 2.4_
  
  - [ ] 4.3 Write property test for diff detection
    - **Property 14: Diff detection accuracy**
    - **Validates: Requirements 2.3, 2.4**
  
  - [ ] 4.4 Implement cache update after successful translation
    - Update FileMetadata with new commit hash and translation info
    - Mark translations as outdated when source changes
    - _Requirements: 2.5_

- [ ] 5. Implement Markdown Parser with protected region detection
  - [ ] 5.1 Create segment detection for protected regions
    - Detect YAML frontmatter (--- to ---)
    - Detect fenced code blocks (``` to ```)
    - Detect inline code (`...`)
    - Detect GitBook tags ({% ... %}, {{ ... }})
    - Detect HTML tags and attributes
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 4.1, 4.2_
  
  - [ ] 5.2 Implement link and image path protection
    - Parse Markdown links [text](URL) and protect URL
    - Parse image references ![alt](path) and protect path
    - Detect and protect relative paths, anchors, file references
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ] 5.3 Capture structure information
    - Record line breaks, indentation, and whitespace patterns
    - Store in StructureInfo for reconstruction
    - _Requirements: 3.1_
  
  - [ ] 5.4 Create segment array with translatable and protected regions
    - Build Segment array with type, content, line numbers
    - Add metadata for protection reasons
    - _Requirements: 4.3, 4.4_
  
  - [ ] 5.5 Write property test for protected region detection
    - **Property 2: Protected region round-trip**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.5**
  
  - [ ] 5.6 Write property test for link URL preservation
    - **Property 3: Link URL preservation**
    - **Validates: Requirements 5.1**
  
  - [ ] 5.7 Write property test for image path preservation
    - **Property 4: Image path preservation**
    - **Validates: Requirements 5.2**
  
  - [ ] 5.8 Write property test for relative path preservation
    - **Property 5: Relative path preservation**
    - **Validates: Requirements 5.3, 5.4, 5.5**

- [ ] 6. Implement Glossary Manager
  - [ ] 6.1 Create glossary file loader and parser
    - Load JSON glossary file from specified path
    - Auto-detect glossary format (analyze structure)
    - Parse into Glossary interface with term mappings
    - _Requirements: 8.1, 8.2_
  
  - [ ] 6.2 Implement term lookup functionality
    - Implement getTranslation(term, targetLang) method
    - Return exact translation from glossary
    - Return null if term not found
    - _Requirements: 8.3_
  
  - [ ] 6.3 Write property test for glossary term consistency
    - **Property 10: Glossary term consistency**
    - **Validates: Requirements 8.3, 8.4**
  
  - [ ] 6.4 Write property test for multi-language glossary application
    - **Property 17: Multi-language glossary application**
    - **Validates: Requirements 15.2**

- [ ] 7. Implement Writer AI component
  - [ ] 7.1 Create LLM client using LangChain
    - Set up LangChain with ChatOpenAI or ChatAnthropic
    - Configure API authentication from environment variables
    - Implement retry logic using LangChain's built-in retry mechanisms
    - Handle timeout errors
    - _Requirements: 9.1, 9.2, 9.3_

  - [ ] 7.2 Build translation prompt template with LangChain
    - Create ChatPromptTemplate with format preservation rules
    - Include glossary terms in prompt
    - Include structure information
    - Emphasize formal, business-appropriate tone
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ] 7.3 Implement translate method
    - Send segments and structure to LLM via LangChain
    - Parse LLM response into translated segments
    - Reconstruct full content with protected regions
    - Validate output structure matches input
    - _Requirements: 9.5_

  - [ ] 7.4 Implement correction method for review feedback
    - Accept List[Issue] from Reviewer AI
    - Generate correction prompt for specific issues
    - Return corrected content
    - _Requirements: 12.2_

  - [ ] 7.5 Write property test for Japanese-only translation
    - **Property 8: Japanese-only translation**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

  - [ ] 7.6 Write property test for technical term preservation
    - **Property 11: Technical term preservation**
    - **Validates: Requirements 8.5**

- [ ] 8. Implement Reviewer AI component
  - [ ] 8.1 Create review prompt template with LangChain
    - Build ChatPromptTemplate with verification checklist
    - Include original and translated content
    - Include glossary for term verification
    - Use PydanticOutputParser for structured JSON output
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ] 8.2 Implement review method
    - Send review request to LLM via LangChain
    - Parse JSON response into List[Issue] using Pydantic
    - Classify issues by severity (BLOCKER, MAJOR, MINOR)
    - Determine if translation is approved
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ] 8.3 Add issue classification logic
    - Classify structural damage, link corruption as BLOCKER
    - Classify semantic errors, glossary violations as MAJOR
    - Classify stylistic improvements as MINOR
    - _Requirements: 11.2, 11.3, 11.4_

  - [ ] 8.4 Write property test for complete translation verification
    - **Property 13: Complete translation**
    - **Validates: Requirements 10.2**

- [ ] 9. Implement Translation Pipeline with correction loop
  - [ ] 9.1 Create translateWithReview orchestration function
    - Call Writer AI for initial translation
    - Call Reviewer AI for quality check
    - Filter BLOCKER and MAJOR issues
    - _Requirements: 10.1, 11.5_
  
  - [ ] 9.2 Implement correction loop logic
    - Loop up to 2 iterations for corrections
    - Send critical issues back to Writer AI
    - Re-submit to Reviewer AI after corrections
    - Proceed after max iterations regardless of remaining issues
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [ ] 9.3 Write property test for whitespace preservation
    - **Property 1: Whitespace preservation**
    - **Validates: Requirements 3.1**
  
  - [ ] 9.4 Write property test for table structure preservation
    - **Property 6: Table structure preservation**
    - **Validates: Requirements 6.1, 6.3, 6.4**
  
  - [ ] 9.5 Write property test for table cell translation
    - **Property 7: Table cell translation**
    - **Validates: Requirements 6.2**
  
  - [ ] 9.6 Write property test for punctuation preservation
    - **Property 9: Punctuation preservation**
    - **Validates: Requirements 7.5**
  
  - [ ] 9.7 Write property test for Markdown validity preservation
    - **Property 12: Markdown validity preservation**
    - **Validates: Requirements 9.5**

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement File Writer component
  - [ ] 11.1 Create output path generation logic
    - Implement suffix naming: <name>.<lang>.md
    - Implement directory naming: /<lang>/<original-path>
    - Preserve relative directory structure
    - _Requirements: 13.1, 13.2, 13.4_

  - [ ] 11.2 Implement file saving with directory creation
    - Create parent directories automatically using pathlib (parents=True, exist_ok=True)
    - Write translated content to file
    - Handle file write errors gracefully
    - _Requirements: 13.3, 13.5_

  - [ ] 11.3 Write property test for file naming consistency
    - **Property 15: File naming consistency**
    - **Validates: Requirements 13.1, 13.2**

  - [ ] 11.4 Write property test for directory structure preservation
    - **Property 16: Directory structure preservation**
    - **Validates: Requirements 13.4**

- [ ] 12. Implement GitHub Pusher component
  - [ ] 12.1 Create branch creation logic
    - Generate branch name: translation/<lang>/<timestamp>
    - Use PyGithub API to create new branch
    - _Requirements: 14.3_

  - [ ] 12.2 Implement file push operations
    - Push translated files to GitHub using PyGithub
    - Handle push_same_repo_direct with user confirmation
    - Handle push_same_repo_new_branch automatically
    - _Requirements: 14.2, 14.3, 14.4_

  - [ ] 12.3 Add error handling for GitHub push
    - Report push errors clearly
    - Ensure local files are saved even if push fails
    - _Requirements: 14.5_

  - [ ] 12.4 Generate PR information
    - Provide branch name and PR creation instructions
    - _Requirements: 14.4_

- [ ] 13. Implement Logger component
  - [ ] 13.1 Create progress logging
    - Log current file, language, and processing stage
    - _Requirements: 16.2_
  
  - [ ] 13.2 Create error logging with context
    - Log errors with file path, language, operation
    - Mask sensitive information (API keys, tokens)
    - _Requirements: 16.1_
  
  - [ ] 13.3 Create issue logging
    - Log all Reviewer AI issues with severity and location
    - _Requirements: 16.3_
  
  - [ ] 13.4 Create summary reporting
    - Generate summary with files processed, translations created, errors
    - Include processing duration
    - _Requirements: 16.4_
  
  - [ ] 13.5 Write property test for log completeness
    - **Property 19: Log completeness**
    - **Validates: Requirements 16.1**
  
  - [ ] 13.6 Write property test for progress logging
    - **Property 20: Progress logging**
    - **Validates: Requirements 16.2**

- [ ] 14. Implement main orchestration and multi-language processing
  - [ ] 14.1 Create main processing loop
    - Load configuration and validate
    - Fetch files from GitHub
    - Detect changes with diff detection
    - Load glossary
    - _Requirements: 1.1, 2.1, 8.1_
  
  - [ ] 14.2 Implement multi-language processing
    - Loop through each target language
    - Process each file through translation pipeline
    - Apply language-specific glossary mappings
    - _Requirements: 15.1, 15.2_
  
  - [ ] 14.3 Add error isolation logic
    - Catch errors for individual files/languages
    - Continue processing remaining files/languages
    - Collect all errors for final report
    - _Requirements: 15.4_
  
  - [ ] 14.4 Implement file saving and optional GitHub push
    - Save all translated files locally
    - Execute GitHub push based on push_option
    - _Requirements: 13.5, 14.1_
  
  - [ ] 14.5 Generate final summary report
    - Report successes and failures for each language
    - Output processing summary with statistics
    - _Requirements: 15.5, 16.4_
  
  - [ ] 14.6 Write property test for error isolation
    - **Property 18: Error isolation**
    - **Validates: Requirements 15.4**

- [ ] 15. Create CLI entry point and documentation
  - [ ] 15.1 Create CLI executable script
    - Set up command-line interface with argparse or click for all parameters
    - Add help text and usage examples
    - Handle process exit codes appropriately
    - Add shebang for direct execution
    - _Requirements: All requirements - user interface_

  - [ ] 15.2 Write README with usage instructions
    - Document all CLI parameters
    - Provide example commands
    - Explain glossary format
    - Include troubleshooting guide
    - Document LangChain configuration and API key setup
    - _Requirements: 16.5_

  - [ ] 15.3 Create example glossary file
    - Provide sample glossary JSON
    - Document glossary format options
    - _Requirements: 8.1, 8.2_

- [ ] 16. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
