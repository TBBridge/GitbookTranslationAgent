"""Property-based tests for LogProgressTool."""

import json
from hypothesis import given, settings, strategies as st

from src.tools.log_progress import LogProgressTool


class TestLogProgressProperty:
    """Property-based tests for LogProgressTool."""

    @given(
        stage=st.text(min_size=1, max_size=50),
        file=st.text(min_size=1, max_size=100),
        language=st.text(min_size=2, max_size=10)
    )
    @settings(max_examples=100)
    def test_progress_logging_completeness(self, stage, file, language):
        """
        Property 20: Progress logging
        
        For any progress log entry with stage, file, and language,
        the log should contain all three pieces of information.
        
        **Validates: Requirements 16.2**
        """
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="progress",
            data={
                "stage": stage,
                "file": file,
                "language": language
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["log_type"] == "progress"
        
        # Verify log entry contains all information
        logs = tool.get_logs()
        assert len(logs) == 1
        
        log_entry = logs[0]
        assert log_entry["type"] == "progress"
        assert log_entry["stage"] == stage
        assert log_entry["file"] == file
        assert log_entry["language"] == language
        assert "message" in log_entry
        assert stage in log_entry["message"]
        assert file in log_entry["message"]
        assert language in log_entry["message"]

    @given(
        error_msg=st.text(min_size=1, max_size=200),
        file=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        language=st.one_of(st.none(), st.text(min_size=2, max_size=10)),
        operation=st.one_of(st.none(), st.text(min_size=1, max_size=50))
    )
    @settings(max_examples=100)
    def test_error_logging_completeness(self, error_msg, file, language, operation):
        """
        Property 19: Log completeness
        
        For any error log entry, the log should contain the error message
        and all available context (file, language, operation).
        
        **Validates: Requirements 16.1**
        """
        tool = LogProgressTool()
        tool.clear_logs()
        
        data = {"error": error_msg}
        if file is not None:
            data["file"] = file
        if language is not None:
            data["language"] = language
        if operation is not None:
            data["operation"] = operation
        
        result_json = tool._run(
            log_type="error",
            data=data
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["log_type"] == "error"
        
        # Verify log entry contains all information
        logs = tool.get_logs()
        assert len(logs) == 1
        
        log_entry = logs[0]
        assert log_entry["type"] == "error"
        assert "error" in log_entry
        assert log_entry["file"] == file
        assert log_entry["language"] == language
        assert log_entry["operation"] == operation
        assert "message" in log_entry

    @given(
        files_processed=st.integers(min_value=0, max_value=1000),
        translations_created=st.integers(min_value=0, max_value=1000),
        errors=st.integers(min_value=0, max_value=100),
        warnings=st.integers(min_value=0, max_value=100),
        duration=st.floats(min_value=0.0, max_value=3600.0)
    )
    @settings(max_examples=100)
    def test_summary_logging_contains_all_metrics(self, files_processed, translations_created, errors, warnings, duration):
        """
        Property: Summary logging contains all metrics
        
        For any summary log entry, the log should contain all metrics:
        files_processed, translations_created, errors, warnings, and duration.
        """
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="summary",
            data={
                "files_processed": files_processed,
                "translations_created": translations_created,
                "errors": errors,
                "warnings": warnings,
                "duration": duration
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["log_type"] == "summary"
        assert result["files_processed"] == files_processed
        assert result["translations_created"] == translations_created
        assert result["errors"] == errors
        assert result["warnings"] == warnings
        assert result["duration"] == duration
        
        # Verify log entry contains all information
        logs = tool.get_logs()
        assert len(logs) == 1
        
        log_entry = logs[0]
        assert log_entry["type"] == "summary"
        assert log_entry["files_processed"] == files_processed
        assert log_entry["translations_created"] == translations_created
        assert log_entry["errors"] == errors
        assert log_entry["warnings"] == warnings
        assert log_entry["duration"] == duration

    @given(
        text=st.text(min_size=1, max_size=500)
    )
    @settings(max_examples=100)
    def test_sensitive_info_masking(self, text):
        """
        Property: Sensitive information is masked
        
        For any error message containing API keys or tokens,
        those sensitive values should be masked in the log.
        """
        tool = LogProgressTool()
        
        # Test masking of various sensitive patterns
        test_cases = [
            ("api_key=sk-1234567890abcdef", "***MASKED_KEY***"),
            ("token=ghp_abcdefghijklmnopqrstuvwxyz1234567890", "***MASKED_TOKEN***"),
            ("password=mysecretpassword", "***MASKED***"),
        ]
        
        for original, expected_mask in test_cases:
            masked = tool._mask_sensitive_info(original)
            # Verify that the sensitive part is masked
            assert expected_mask in masked or "***MASKED" in masked

    @given(
        severity=st.sampled_from(["BLOCKER", "MAJOR", "MINOR"]),
        category=st.text(min_size=1, max_size=20),
        line=st.integers(min_value=1, max_value=10000),
        description=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100)
    def test_issue_logging_contains_all_fields(self, severity, category, line, description):
        """
        Property: Issue logging contains all fields
        
        For any issue log entry, the log should contain severity,
        category, line number, and description.
        """
        tool = LogProgressTool()
        tool.clear_logs()
        
        result_json = tool._run(
            log_type="issue",
            data={
                "severity": severity,
                "category": category,
                "line": line,
                "description": description
            }
        )
        
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["log_type"] == "issue"
        assert result["severity"] == severity
        
        # Verify log entry contains all information
        logs = tool.get_logs()
        assert len(logs) == 1
        
        log_entry = logs[0]
        assert log_entry["type"] == "issue"
        assert log_entry["severity"] == severity
        assert log_entry["category"] == category
        assert log_entry["line"] == line
        assert log_entry["description"] == description
        assert "message" in log_entry
