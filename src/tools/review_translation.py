"""Tool for reviewing translation quality."""

import os
import json
import re
from typing import Dict, Any, Optional, List

from langchain.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from ..models.review_models import (
    ReviewRequest,
    ReviewResult,
    Issue,
    IssueSeverity,
    IssueCategory,
    IssueLocation,
)
from ..models.glossary_models import Glossary


class ReviewTranslationInput(BaseModel):
    """Input schema for ReviewTranslationTool."""

    original_content: str = Field(description="Original content before translation")
    translated_content: str = Field(description="Translated content to review")
    target_language: str = Field(description="Target language code (e.g., 'en', 'zh-CN')")
    glossary: Dict[str, Any] = Field(description="Glossary with term mappings")


class IssueOutput(BaseModel):
    """Output schema for a single issue."""

    severity: str = Field(description="Issue severity: BLOCKER, MAJOR, or MINOR")
    category: str = Field(description="Issue category: format, completeness, terminology, links, or style")
    line: int = Field(description="Line number where issue occurs")
    column: Optional[int] = Field(default=None, description="Column number where issue occurs (optional)")
    description: str = Field(description="Description of the issue")
    suggestion: Optional[str] = Field(default=None, description="Suggestion for fixing the issue (optional)")


class ReviewOutput(BaseModel):
    """Output schema for review result."""

    issues: List[IssueOutput] = Field(description="List of issues found during review")
    approved: bool = Field(description="Whether the translation is approved (true if no BLOCKER or MAJOR issues)")


class ReviewTranslationTool(BaseTool):
    """Tool for reviewing translation quality using LLM."""

    name: str = "review_translation"
    description: str = """
    Reviews translated content for quality and completeness.
    Verifies format preservation, completeness, terminology, links, and style.
    Input should be a JSON with: original_content (string), translated_content (string), target_language (string), glossary (dict).
    Returns list of issues with severity (BLOCKER/MAJOR/MINOR) and approval status.
    """
    args_schema: type[BaseModel] = ReviewTranslationInput

    # LLM client (initialized in __init__)
    llm: Optional[ChatGoogleGenerativeAI] = None
    # Prompt template (initialized in __init__)
    prompt_template: Optional[ChatPromptTemplate] = None
    # Output parser (initialized in __init__)
    output_parser: Optional[PydanticOutputParser] = None

    def __init__(self, **kwargs):
        """Initialize the tool with LLM client and prompt template."""
        super().__init__(**kwargs)
        
        # Initialize LangChain ChatGoogleGenerativeAI
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            # Try alternative environment variable
            api_key = os.environ.get("GEMINI_API_KEY")
        
        # Initialize with retry logic and timeout
        # Use Gemini Pro for review to ensure thorough quality checking
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.1,  # Very low temperature for consistent, objective review
            max_retries=3,  # Retry up to 3 times with exponential backoff
            request_timeout=120,  # 120 second timeout for review requests
            google_api_key=api_key
        )
        
        # Initialize PydanticOutputParser for structured JSON output
        self.output_parser = PydanticOutputParser(pydantic_object=ReviewOutput)
        
        # Build review prompt template with verification checklist
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a quality assurance reviewer for technical documentation translation.

Task: Review the translation for quality and completeness.

Verification Checklist:
1. Format Preservation: Verify that all GitBook syntax, tags, line breaks, indentation, tables, and code blocks are preserved exactly as in the original
2. Completeness: Check for any untranslated Japanese text (outside of protected regions like code blocks) and ensure no lines are missing
3. Terminology: Verify that glossary terms are used consistently without variation throughout the translation
4. Links: Ensure all URLs, relative paths, and anchor links remain unchanged from the original
5. Style: Confirm the translation uses formal, natural language appropriate for {target_language}

Issue Severity Guidelines:
- BLOCKER: Structural damage, link corruption, missing content, code modification, or protected region changes
- MAJOR: Semantic errors, glossary violations, untranslated Japanese text, or incorrect terminology
- MINOR: Stylistic improvements, minor phrasing adjustments, or formatting suggestions

Glossary Terms to Verify:
{glossary_terms}

{format_instructions}

IMPORTANT: You must respond ONLY with valid JSON matching the specified format. Do not include any explanatory text before or after the JSON."""),
            ("user", """Original Content:
{original_content}

Translated Content:
{translated_content}

Review the translation and output issues in the specified JSON format. If no issues are found, return an empty issues array with approved set to true.""")
        ])

    def _classify_issue_severity(self, category: str, description: str) -> str:
        """Classify issue severity based on category and description.
        
        This method implements explicit classification rules per Requirements 11.2, 11.3, 11.4:
        - BLOCKER: Structural damage, link corruption, missing content, code modification
        - MAJOR: Semantic errors, glossary violations
        - MINOR: Stylistic improvements
        
        Args:
            category: Issue category (format, completeness, terminology, links, style)
            description: Issue description text
            
        Returns:
            Severity level: "BLOCKER", "MAJOR", or "MINOR"
        """
        description_lower = description.lower()
        
        # BLOCKER issues (Requirements 11.2):
        # - Structural damage
        blocker_keywords = [
            "structural", "structure", "broken", "damaged", "corrupted",
            "code block", "fenced code", "yaml", "frontmatter",
            "table structure", "markdown invalid", "syntax error"
        ]
        
        # - Link corruption
        link_corruption_keywords = [
            "link", "url", "href", "path", "anchor", "reference",
            "modified", "changed", "incorrect", "broken link"
        ]
        
        # - Missing content
        missing_content_keywords = [
            "missing", "deleted", "removed", "lost", "absent",
            "incomplete", "truncated"
        ]
        
        # - Code modification
        code_modification_keywords = [
            "code modified", "code changed", "code altered",
            "inline code", "protected region"
        ]
        
        # Check for BLOCKER conditions
        if category == "format":
            # Format issues are typically BLOCKER if they involve structural damage
            if any(keyword in description_lower for keyword in blocker_keywords):
                return "BLOCKER"
        
        if category == "links":
            # Link issues are BLOCKER if links are corrupted/modified
            if any(keyword in description_lower for keyword in link_corruption_keywords):
                return "BLOCKER"
        
        if category == "completeness":
            # Completeness issues are BLOCKER if content is missing
            if any(keyword in description_lower for keyword in missing_content_keywords):
                return "BLOCKER"
        
        # Code modification is always BLOCKER
        if any(keyword in description_lower for keyword in code_modification_keywords):
            return "BLOCKER"
        
        # MAJOR issues (Requirements 11.3):
        # - Semantic errors
        semantic_error_keywords = [
            "semantic", "meaning", "incorrect translation", "wrong translation",
            "mistranslation", "inaccurate", "error", "untranslated"
        ]
        
        # - Glossary violations
        glossary_violation_keywords = [
            "glossary", "terminology", "term", "inconsistent",
            "should use", "must use"
        ]
        
        # Check for MAJOR conditions
        if category == "terminology":
            # Terminology issues are typically MAJOR (glossary violations)
            return "MAJOR"
        
        if category == "completeness":
            # Untranslated text is MAJOR
            if "untranslated" in description_lower or "japanese" in description_lower:
                return "MAJOR"
        
        if any(keyword in description_lower for keyword in semantic_error_keywords):
            return "MAJOR"
        
        if any(keyword in description_lower for keyword in glossary_violation_keywords):
            return "MAJOR"
        
        # MINOR issues (Requirements 11.4):
        # - Stylistic improvements
        # Everything else defaults to MINOR (style category or unclassified)
        return "MINOR"

    def _format_glossary_terms(self, glossary: Dict[str, Any], target_language: str) -> str:
        """Format glossary terms for inclusion in the prompt.
        
        Args:
            glossary: Glossary dictionary with term mappings
            target_language: Target language code
            
        Returns:
            Formatted string of glossary terms
        """
        if not glossary or "mappings" not in glossary:
            return "No glossary terms provided."
        
        mappings = glossary.get("mappings", {})
        if not mappings:
            return "No glossary terms provided."
        
        formatted_terms = []
        for term, translations in mappings.items():
            if target_language in translations:
                target_term = translations[target_language]
                formatted_terms.append(f"  - {term} → {target_term}")
        
        if not formatted_terms:
            return f"No glossary terms available for language: {target_language}"
        
        return "\n".join(formatted_terms)

    def _run(
        self,
        original_content: str,
        translated_content: str,
        target_language: str,
        glossary: Dict[str, Any]
    ) -> str:
        """Execute the tool to review translation.
        
        Args:
            original_content: Original content before translation
            translated_content: Translated content to review
            target_language: Target language code
            glossary: Glossary dictionary with term mappings
            
        Returns:
            JSON string containing issues list and approval status
        """
        # Format glossary terms for the prompt
        glossary_terms = self._format_glossary_terms(glossary, target_language)
        
        # Get format instructions from the output parser
        format_instructions = self.output_parser.get_format_instructions()
        
        # Format the prompt with all required variables
        formatted_prompt = self.prompt_template.format_messages(
            target_language=target_language,
            glossary_terms=glossary_terms,
            format_instructions=format_instructions,
            original_content=original_content,
            translated_content=translated_content
        )
        
        # Send review request to LLM via LangChain
        try:
            response = self.llm.invoke(formatted_prompt)
            response_text = response.content
            
            # Parse JSON response into ReviewOutput using Pydantic
            try:
                review_output = self.output_parser.parse(response_text)
            except Exception as parse_error:
                # If parsing fails, try to extract JSON from the response
                # Sometimes LLMs add extra text around the JSON
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    review_output = self.output_parser.parse(json_str)
                else:
                    raise ValueError(f"Failed to parse LLM response as JSON: {parse_error}")
            
            # Validate and potentially reclassify issues based on explicit classification rules
            # This ensures consistency with Requirements 11.2, 11.3, 11.4
            for issue in review_output.issues:
                # Get the expected severity based on our classification logic
                expected_severity = self._classify_issue_severity(
                    issue.category,
                    issue.description
                )
                
                # If LLM's classification differs from our rules, use our classification
                # This ensures consistent enforcement of the specification
                if issue.severity != expected_severity:
                    issue.severity = expected_severity
            
            # Classify issues by severity and determine approval
            # Approval is false if there are any BLOCKER or MAJOR issues
            has_blocker_or_major = any(
                issue.severity in ["BLOCKER", "MAJOR"]
                for issue in review_output.issues
            )
            
            # Override approval status based on issue severity
            # The LLM might set approved=true even with BLOCKER/MAJOR issues
            if has_blocker_or_major:
                review_output.approved = False
            elif not review_output.issues:
                # No issues means approved
                review_output.approved = True
            
            # Convert ReviewOutput to JSON string
            result = {
                "issues": [
                    {
                        "severity": issue.severity,
                        "category": issue.category,
                        "line": issue.line,
                        "column": issue.column,
                        "description": issue.description,
                        "suggestion": issue.suggestion
                    }
                    for issue in review_output.issues
                ],
                "approved": review_output.approved
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            # Handle LLM API errors
            error_result = {
                "issues": [
                    {
                        "severity": "BLOCKER",
                        "category": "format",
                        "line": 0,
                        "column": None,
                        "description": f"Review failed due to error: {str(e)}",
                        "suggestion": "Please retry the review or check the LLM API configuration."
                    }
                ],
                "approved": False
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)

    async def _arun(self, *args, **kwargs) -> str:
        """Async execution (not implemented)."""
        raise NotImplementedError("Async execution not supported")
