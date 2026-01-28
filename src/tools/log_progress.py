"""Tool for logging progress and errors."""

import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from langchain.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from ..models.review_models import Issue, IssueSeverity
from ..models.log_models import LogContext, ProcessingSummary


class LogType(Enum):
    """Types of log messages."""

    PROGRESS = "progress"
    ERROR = "error"
    ISSUE = "issue"
    SUMMARY = "summary"


class LogProgressInput(BaseModel):
    """Input schema for LogProgressTool."""

    log_type: str = Field(
        description="Type of log: 'progress', 'error', 'issue', or 'summary'"
    )
    data: Dict[str, Any] = Field(description="Log data as dictionary")


class LogProgressTool(BaseTool):
    """Tool for logging progress, errors, and summaries."""

    name: str = "log_progress"
    description: str = """
    Logs progress, errors, issues, and summaries during translation.
    Input should be a JSON with: log_type (string: 'progress'|'error'|'issue'|'summary'), data (dict).
    Returns confirmation of logged message.
    """
    args_schema: type[BaseModel] = LogProgressInput
    logger: object = Field(default_factory=lambda: None, exclude=True)
    logs: list = Field(default_factory=list, exclude=True)

    def __init__(self, **kwargs):
        """Initialize the tool with a logger."""
        super().__init__(**kwargs)
        self.logger = self._setup_logger()
        self.logs = []  # Store logs for testing and summary

    def _setup_logger(self) -> logging.Logger:
        """Set up the logger with appropriate handlers."""
        logger = logging.getLogger("gitbook_translator")
        
        # Only add handlers if they don't exist
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger

    def _run(self, log_type: str, data: Dict[str, Any]) -> str:
        """Execute the tool to log messages.
        
        Args:
            log_type: Type of log message ('progress', 'error', 'issue', 'summary')
            data: Dictionary containing log data
            
        Returns:
            JSON string with confirmation of logged message
        """
        try:
            log_type_enum = LogType(log_type.lower())
        except ValueError:
            return json.dumps({
                "success": False,
                "error": f"Invalid log_type: {log_type}. Must be one of: progress, error, issue, summary"
            })

        try:
            if log_type_enum == LogType.PROGRESS:
                return self._log_progress(data)
            elif log_type_enum == LogType.ERROR:
                return self._log_error(data)
            elif log_type_enum == LogType.ISSUE:
                return self._log_issue(data)
            elif log_type_enum == LogType.SUMMARY:
                return self._log_summary(data)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error logging message: {str(e)}"
            })

    def _log_progress(self, data: Dict[str, Any]) -> str:
        """Log progress information.
        
        Args:
            data: Dictionary with keys: stage, file, language
            
        Returns:
            JSON confirmation
        """
        stage = data.get("stage", "unknown")
        file = data.get("file", "unknown")
        language = data.get("language", "unknown")
        
        message = f"[{stage}] Processing {file} for {language}"
        self.logger.info(message)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "progress",
            "stage": stage,
            "file": file,
            "language": language,
            "message": message
        }
        self.logs.append(log_entry)
        
        return json.dumps({
            "success": True,
            "log_type": "progress",
            "message": message
        })

    def _log_error(self, data: Dict[str, Any]) -> str:
        """Log error information with context.
        
        Args:
            data: Dictionary with keys: error, file (optional), language (optional), operation (optional)
            
        Returns:
            JSON confirmation
        """
        error = data.get("error", "Unknown error")
        file = data.get("file")
        language = data.get("language")
        operation = data.get("operation")
        
        # Mask sensitive information (API keys, tokens)
        error_masked = self._mask_sensitive_info(str(error))
        
        # Build context string
        context_parts = []
        if file:
            context_parts.append(f"file={file}")
        if language:
            context_parts.append(f"language={language}")
        if operation:
            context_parts.append(f"operation={operation}")
        
        context_str = f" ({', '.join(context_parts)})" if context_parts else ""
        message = f"ERROR: {error_masked}{context_str}"
        
        self.logger.error(message)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "error": error_masked,
            "file": file,
            "language": language,
            "operation": operation,
            "message": message
        }
        self.logs.append(log_entry)
        
        return json.dumps({
            "success": True,
            "log_type": "error",
            "message": message
        })

    def _log_issue(self, data: Dict[str, Any]) -> str:
        """Log issue information from Reviewer AI.
        
        Args:
            data: Dictionary with keys: severity, category, line, description, suggestion (optional)
            
        Returns:
            JSON confirmation
        """
        severity = data.get("severity", "UNKNOWN")
        category = data.get("category", "unknown")
        line = data.get("line", "?")
        description = data.get("description", "No description")
        suggestion = data.get("suggestion")
        
        message = f"[{severity}] {category.upper()} at line {line}: {description}"
        if suggestion:
            message += f" (Suggestion: {suggestion})"
        
        # Log at appropriate level based on severity
        if severity == "BLOCKER":
            self.logger.error(message)
        elif severity == "MAJOR":
            self.logger.warning(message)
        else:
            self.logger.info(message)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "issue",
            "severity": severity,
            "category": category,
            "line": line,
            "description": description,
            "suggestion": suggestion,
            "message": message
        }
        self.logs.append(log_entry)
        
        return json.dumps({
            "success": True,
            "log_type": "issue",
            "severity": severity,
            "message": message
        })

    def _log_summary(self, data: Dict[str, Any]) -> str:
        """Log processing summary.
        
        Args:
            data: Dictionary with keys: files_processed, translations_created, errors, warnings, duration
            
        Returns:
            JSON confirmation
        """
        files_processed = data.get("files_processed", 0)
        translations_created = data.get("translations_created", 0)
        errors = data.get("errors", 0)
        warnings = data.get("warnings", 0)
        duration = data.get("duration", 0)
        
        summary_lines = [
            "=" * 60,
            "PROCESSING SUMMARY",
            "=" * 60,
            f"Files processed: {files_processed}",
            f"Translations created: {translations_created}",
            f"Errors: {errors}",
            f"Warnings: {warnings}",
            f"Duration: {duration:.2f} seconds",
            "=" * 60
        ]
        
        message = "\n".join(summary_lines)
        self.logger.info(message)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "summary",
            "files_processed": files_processed,
            "translations_created": translations_created,
            "errors": errors,
            "warnings": warnings,
            "duration": duration,
            "message": message
        }
        self.logs.append(log_entry)
        
        return json.dumps({
            "success": True,
            "log_type": "summary",
            "files_processed": files_processed,
            "translations_created": translations_created,
            "errors": errors,
            "warnings": warnings,
            "duration": duration
        })

    def _mask_sensitive_info(self, text: str) -> str:
        """Mask sensitive information like API keys and tokens.
        
        Args:
            text: Text that may contain sensitive information
            
        Returns:
            Text with sensitive information masked
        """
        # Mask API keys and tokens
        text = re.sub(r'(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,}]+', 
                     r'\1=***MASKED***', text, flags=re.IGNORECASE)
        
        # Mask GitHub tokens (40+ hex characters)
        text = re.sub(r'ghp_[a-zA-Z0-9_]{36,}', '***MASKED_TOKEN***', text)
        
        # Mask OpenAI keys
        text = re.sub(r'sk-[a-zA-Z0-9_-]{40,}', '***MASKED_KEY***', text)
        
        return text

    def get_logs(self) -> list:
        """Get all logged messages (for testing).
        
        Returns:
            List of log entries
        """
        return self.logs

    def clear_logs(self) -> None:
        """Clear all logged messages (for testing)."""
        self.logs = []

    async def _arun(self, *args, **kwargs) -> str:
        """Async execution (not implemented)."""
        raise NotImplementedError("Async execution not supported")
