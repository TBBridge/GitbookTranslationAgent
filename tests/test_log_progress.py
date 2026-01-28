"""Unit tests for LogProgressTool."""

import json
import pytest

from src.tools.log_progress import LogProgressTool


class TestLogProgressTool:
    """Test suite for LogProgressTool."""

    def test_log_progress_basic(self):
        """Test basic progress logging."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="progress",
            data={
                "stage": "parsing",
                "file": "docs/intro.md",
                "language": "en"
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["log_type"] == "progress"
        assert "docs/intro.md" in result["message"]
        assert "en" in result["message"]
        assert "parsing" in result["message"]
        
        # Verify log was stored
        logs = tool.get_logs()
        assert len(logs) == 1
        assert logs[0]["type"] == "progress"
        assert logs[0]["file"] == "docs/intro.md"
        assert logs[0]["language"] == "en"
        assert logs[0]["stage"] == "parsing"

    def test_log_error_with_context(self):
        """Test error logging with full context."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="error",
            data={
                "error": "Failed to fetch file",
                "file": "docs/test.md",
                "language": "en",
                "operation": "fetch_github_files"
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["log_type"] == "error"
        assert "Failed to fetch file" in result["message"]
        
        # Verify log was stored with all context
        logs = tool.get_logs()
        assert len(logs) == 1
        assert logs[0]["type"] == "error"
        assert logs[0]["file"] == "docs/test.md"
        assert logs[0]["language"] == "en"
        assert logs[0]["operation"] == "fetch_github_files"

    def test_log_error_without_context(self):
        """Test error logging without optional context."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="error",
            data={
                "error": "Generic error occurred"
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["log_type"] == "error"
        
        # Verify log was stored with None values for optional fields
        logs = tool.get_logs()
        assert len(logs) == 1
        assert logs[0]["file"] is None
        assert logs[0]["language"] is None
        assert logs[0]["operation"] is None

    def test_log_issue_blocker(self):
        """Test logging a BLOCKER issue."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="issue",
            data={
                "severity": "BLOCKER",
                "category": "format",
                "line": 42,
                "description": "Code block not preserved",
                "suggestion": "Check protected region detection"
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["log_type"] == "issue"
        assert result["severity"] == "BLOCKER"
        
        # Verify log was stored
        logs = tool.get_logs()
        assert len(logs) == 1
        assert logs[0]["severity"] == "BLOCKER"
        assert logs[0]["category"] == "format"
        assert logs[0]["line"] == 42
        assert logs[0]["description"] == "Code block not preserved"
        assert logs[0]["suggestion"] == "Check protected region detection"

    def test_log_issue_major(self):
        """Test logging a MAJOR issue."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="issue",
            data={
                "severity": "MAJOR",
                "category": "terminology",
                "line": 15,
                "description": "Glossary term not applied"
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["severity"] == "MAJOR"
        
        logs = tool.get_logs()
        assert len(logs) == 1
        assert logs[0]["severity"] == "MAJOR"

    def test_log_issue_minor(self):
        """Test logging a MINOR issue."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="issue",
            data={
                "severity": "MINOR",
                "category": "style",
                "line": 8,
                "description": "Inconsistent spacing"
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["severity"] == "MINOR"
        
        logs = tool.get_logs()
        assert len(logs) == 1
        assert logs[0]["severity"] == "MINOR"

    def test_log_summary(self):
        """Test summary logging."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="summary",
            data={
                "files_processed": 10,
                "translations_created": 30,
                "errors": 2,
                "warnings": 5,
                "duration": 125.5
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["log_type"] == "summary"
        assert result["files_processed"] == 10
        assert result["translations_created"] == 30
        assert result["errors"] == 2
        assert result["warnings"] == 5
        assert result["duration"] == 125.5
        
        # Verify log was stored
        logs = tool.get_logs()
        assert len(logs) == 1
        assert logs[0]["type"] == "summary"
        assert logs[0]["files_processed"] == 10
        assert logs[0]["translations_created"] == 30

    def test_invalid_log_type(self):
        """Test error handling for invalid log type."""
        tool = LogProgressTool()
        
        result_json = tool._run(
            log_type="invalid_type",
            data={}
        )
        
        result = json.loads(result_json)
        assert result["success"] is False
        assert "Invalid log_type" in result["error"]

    def test_mask_api_key(self):
        """Test masking of API keys."""
        tool = LogProgressTool()
        
        text = "Failed with api_key=sk-1234567890abcdefghijklmnopqrstuvwxyz"
        masked = tool._mask_sensitive_info(text)
        
        assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in masked
        assert "***MASKED" in masked

    def test_mask_github_token(self):
        """Test masking of GitHub tokens."""
        tool = LogProgressTool()
        
        text = "Authentication failed with token ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        masked = tool._mask_sensitive_info(text)
        
        assert "ghp_abcdefghijklmnopqrstuvwxyz1234567890" not in masked
        assert "***MASKED" in masked

    def test_mask_password(self):
        """Test masking of passwords."""
        tool = LogProgressTool()
        
        text = "Connection error: password=mysecretpassword123"
        masked = tool._mask_sensitive_info(text)
        
        assert "mysecretpassword123" not in masked
        assert "***MASKED" in masked

    def test_multiple_logs_accumulate(self):
        """Test that multiple logs accumulate correctly."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        # Log multiple messages
        tool._run(log_type="progress", data={"stage": "start", "file": "a.md", "language": "en"})
        tool._run(log_type="progress", data={"stage": "translate", "file": "a.md", "language": "en"})
        tool._run(log_type="error", data={"error": "Test error"})
        tool._run(log_type="summary", data={
            "files_processed": 1,
            "translations_created": 1,
            "errors": 1,
            "warnings": 0,
            "duration": 10.5
        })
        
        logs = tool.get_logs()
        assert len(logs) == 4
        assert logs[0]["type"] == "progress"
        assert logs[1]["type"] == "progress"
        assert logs[2]["type"] == "error"
        assert logs[3]["type"] == "summary"

    def test_clear_logs(self):
        """Test clearing logs."""
        tool = LogProgressTool()
        
        # Add some logs
        tool._run(log_type="progress", data={"stage": "test", "file": "test.md", "language": "en"})
        assert len(tool.get_logs()) == 1
        
        # Clear logs
        tool.clear_logs()
        assert len(tool.get_logs()) == 0

    def test_log_formatting(self):
        """Test that log messages are properly formatted."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        tool._run(
            log_type="progress",
            data={
                "stage": "review",
                "file": "docs/guide.md",
                "language": "zh-CN"
            }
        )
        
        logs = tool.get_logs()
        message = logs[0]["message"]
        
        # Verify message contains all key information
        assert "[review]" in message
        assert "docs/guide.md" in message
        assert "zh-CN" in message

    def test_issue_without_suggestion(self):
        """Test logging an issue without a suggestion."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="issue",
            data={
                "severity": "MINOR",
                "category": "style",
                "line": 5,
                "description": "Minor formatting issue"
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        
        logs = tool.get_logs()
        assert logs[0]["suggestion"] is None

    def test_summary_with_zero_values(self):
        """Test summary logging with zero values."""
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="summary",
            data={
                "files_processed": 0,
                "translations_created": 0,
                "errors": 0,
                "warnings": 0,
                "duration": 0.0
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["files_processed"] == 0
        assert result["translations_created"] == 0
        assert result["errors"] == 0
        assert result["warnings"] == 0
        assert result["duration"] == 0.0
