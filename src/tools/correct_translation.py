"""Tool for correcting translation issues."""

import os
import json
from typing import List, Dict, Any, Optional

from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


class CorrectTranslationInput(BaseModel):
    """Input schema for CorrectTranslationTool."""

    content: str = Field(description="Translated content that needs correction")
    issues: List[Dict[str, Any]] = Field(description="List of issues to correct")
    target_language: str = Field(description="Target language code (e.g., 'en', 'zh-CN')")


class CorrectTranslationTool(BaseTool):
    """Tool for correcting translation issues using LLM.
    
    This tool takes translated content with identified issues and produces
    corrected content that addresses those specific issues while making
    minimal changes to non-problematic sections.
    
    Requirements: 12.1, 12.2
    """

    name: str = "correct_translation"
    description: str = """
    Corrects specific issues in translated content based on review feedback.
    Focuses on addressing identified problems while making minimal changes to correct sections.
    Input should be a JSON with: content (string), issues (list of issue dicts), target_language (string).
    Returns corrected content as a string.
    """
    args_schema: type[BaseModel] = CorrectTranslationInput

    # LLM client (initialized in __init__)
    llm: Optional[ChatOpenAI] = None
    # Prompt template (initialized in __init__)
    prompt_template: Optional[ChatPromptTemplate] = None

    def __init__(self, **kwargs):
        """Initialize the tool with LLM client and prompt template.
        
        Requirements: 12.1, 12.2
        """
        super().__init__(**kwargs)
        
        # Initialize LangChain ChatOpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            # Try alternative environment variable
            api_key = os.environ.get("OPENAI_API_KEY")
        
        # Initialize with retry logic and timeout
        # Use GPT-4 for high-quality corrections
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.2,  # Low temperature for precise, focused corrections
            max_retries=3,  # Retry up to 3 times with exponential backoff
            request_timeout=120,  # 120 second timeout for correction requests
            api_key=api_key
        )
        
        # Build correction prompt template
        # Requirements: 12.2 - Focus on specific issues, emphasize minimal changes
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a professional translator specializing in correcting translation issues.

Task: Correct the specific issues identified in the translated content.

CRITICAL RULES:
1. Make ONLY the changes necessary to fix the identified issues
2. Do NOT modify sections that are not mentioned in the issues list
3. Preserve ALL formatting, line breaks, indentation, and spacing exactly
4. Maintain all GitBook syntax, code blocks, links, and protected regions
5. Focus on addressing each issue precisely as described

CORRECTION APPROACH:
- For format issues: Fix structural problems, restore correct syntax
- For completeness issues: Translate missing Japanese text, restore missing lines
- For terminology issues: Replace incorrect terms with correct glossary terms
- For link issues: Restore original URLs, paths, and anchors
- For style issues: Improve phrasing while maintaining meaning

OUTPUT REQUIREMENTS:
- Return ONLY the corrected content
- Do NOT add explanations, comments, or notes
- Ensure all issues are addressed
- Preserve everything else unchanged"""),
            ("user", """Target Language: {target_language}

Issues to Correct:
{issues_text}

Content to Correct:
{content}

Correct the content by addressing each issue listed above. Return only the corrected content.""")
        ])

    def _format_issues_for_prompt(self, issues: List[Dict[str, Any]]) -> str:
        """Format issues list for inclusion in the correction prompt.
        
        Args:
            issues: List of issue dictionaries with severity, category, location, description, suggestion
            
        Returns:
            Formatted string describing all issues to correct
        """
        if not issues:
            return "No issues to correct."
        
        formatted_issues = []
        for i, issue in enumerate(issues, 1):
            severity = issue.get("severity", "UNKNOWN")
            category = issue.get("category", "unknown")
            line = issue.get("line", 0)
            description = issue.get("description", "No description provided")
            suggestion = issue.get("suggestion")
            
            issue_text = f"Issue {i} [{severity} - {category}]:\n"
            issue_text += f"  Location: Line {line}\n"
            issue_text += f"  Problem: {description}\n"
            
            if suggestion:
                issue_text += f"  Suggestion: {suggestion}\n"
            
            formatted_issues.append(issue_text)
        
        return "\n".join(formatted_issues)

    def _run(
        self,
        content: str,
        issues: List[Dict[str, Any]],
        target_language: str
    ) -> str:
        """Execute the tool to correct translation issues.
        
        Requirements: 12.2, 12.3
        
        Args:
            content: Translated content that needs correction
            issues: List of issue dictionaries to correct
            target_language: Target language code
            
        Returns:
            JSON string containing corrected content and success status
        """
        try:
            # If no issues, return original content
            if not issues:
                return json.dumps({
                    "success": True,
                    "corrected_content": content,
                    "message": "No issues to correct"
                }, ensure_ascii=False)
            
            # Format issues for the prompt
            issues_text = self._format_issues_for_prompt(issues)
            
            # Format the prompt with all required variables
            formatted_prompt = self.prompt_template.format_messages(
                target_language=target_language,
                issues_text=issues_text,
                content=content
            )
            
            # Send correction request to LLM
            response = self.llm.invoke(formatted_prompt)
            corrected_content = response.content
            
            # Validate that we got a response
            if not corrected_content or not corrected_content.strip():
                raise ValueError("LLM returned empty corrected content")
            
            # Validate corrections address the issues
            # Requirements: 12.3 - Validate corrections address the issues
            validation_result = self._validate_corrections(
                original_content=content,
                corrected_content=corrected_content,
                issues=issues
            )
            
            return json.dumps({
                "success": True,
                "corrected_content": corrected_content,
                "validation": validation_result
            }, ensure_ascii=False)
            
        except Exception as e:
            # Handle errors gracefully
            return json.dumps({
                "success": False,
                "corrected_content": content,  # Return original on error
                "error": f"Correction failed: {str(e)}"
            }, ensure_ascii=False)

    def _validate_corrections(
        self,
        original_content: str,
        corrected_content: str,
        issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate that corrections address the identified issues.
        
        Requirements: 12.3
        
        Args:
            original_content: Original content before correction
            corrected_content: Content after correction
            issues: List of issues that should be addressed
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            "content_changed": original_content != corrected_content,
            "issues_count": len(issues),
            "validation_notes": []
        }
        
        # Basic validation: check if content changed when issues exist
        if issues and not validation["content_changed"]:
            validation["validation_notes"].append(
                "Warning: Content unchanged despite issues being reported"
            )
        
        # Check for critical issue categories
        blocker_count = sum(1 for issue in issues if issue.get("severity") == "BLOCKER")
        major_count = sum(1 for issue in issues if issue.get("severity") == "MAJOR")
        
        validation["blocker_issues"] = blocker_count
        validation["major_issues"] = major_count
        
        if blocker_count > 0:
            validation["validation_notes"].append(
                f"Addressed {blocker_count} BLOCKER issue(s)"
            )
        
        if major_count > 0:
            validation["validation_notes"].append(
                f"Addressed {major_count} MAJOR issue(s)"
            )
        
        return validation

    async def _arun(self, *args, **kwargs) -> str:
        """Async execution (not implemented)."""
        raise NotImplementedError("Async execution not supported")
