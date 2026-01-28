"""Unit tests for monitoring and observability features."""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

from src.agent.monitoring import (
    MetricsCollector,
    LangChainTracer,
    ExecutionMetrics,
    FileProcessingMetric,
    ToolCallMetric,
    TokenUsage,
)


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""
    
    def test_token_usage_initialization(self):
        """Test TokenUsage initialization with explicit values."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
        
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
    
    def test_token_usage_auto_calculation(self):
        """Test TokenUsage auto-calculates total tokens."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=0)
        
        assert usage.total_tokens == 150
    
    def test_token_usage_zero_tokens(self):
        """Test TokenUsage with zero tokens."""
        usage = TokenUsage()
        
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


class TestToolCallMetric:
    """Tests for ToolCallMetric."""
    
    def test_tool_call_metric_initialization(self):
        """Test ToolCallMetric initialization."""
        start_time = time.time()
        metric = ToolCallMetric(tool_name="TestTool", start_time=start_time)
        
        assert metric.tool_name == "TestTool"
        assert metric.start_time == start_time
        assert metric.end_time is None
        assert metric.duration_seconds is None
        assert metric.success is True
        assert metric.error is None
    
    def test_tool_call_metric_complete_success(self):
        """Test completing a successful tool call metric."""
        start_time = time.time()
        metric = ToolCallMetric(tool_name="TestTool", start_time=start_time)
        
        time.sleep(0.01)  # Small delay to ensure duration > 0
        metric.complete(success=True)
        
        assert metric.end_time is not None
        assert metric.duration_seconds is not None
        assert metric.duration_seconds > 0
        assert metric.success is True
        assert metric.error is None
    
    def test_tool_call_metric_complete_failure(self):
        """Test completing a failed tool call metric."""
        start_time = time.time()
        metric = ToolCallMetric(tool_name="TestTool", start_time=start_time)
        
        metric.complete(success=False, error="Test error")
        
        assert metric.success is False
        assert metric.error == "Test error"


class TestFileProcessingMetric:
    """Tests for FileProcessingMetric."""
    
    def test_file_processing_metric_initialization(self):
        """Test FileProcessingMetric initialization."""
        start_time = time.time()
        metric = FileProcessingMetric(
            file_path="test.md",
            language="en",
            start_time=start_time
        )
        
        assert metric.file_path == "test.md"
        assert metric.language == "en"
        assert metric.start_time == start_time
        assert metric.tool_calls == []
        assert metric.total_tokens == 0
    
    def test_file_processing_metric_complete(self):
        """Test completing file processing metric."""
        start_time = time.time()
        metric = FileProcessingMetric(
            file_path="test.md",
            language="en",
            start_time=start_time
        )
        
        # Add tool calls
        tool_call = ToolCallMetric(tool_name="TranslateTool", start_time=time.time())
        tool_call.input_tokens = 100
        tool_call.output_tokens = 50
        metric.tool_calls.append(tool_call)
        
        time.sleep(0.01)
        metric.complete(success=True)
        
        assert metric.end_time is not None
        assert metric.duration_seconds is not None
        assert metric.success is True
        assert metric.total_tokens == 150  # 100 + 50
    
    def test_file_processing_metric_complete_failure(self):
        """Test completing file processing metric with failure."""
        start_time = time.time()
        metric = FileProcessingMetric(
            file_path="test.md",
            language="en",
            start_time=start_time
        )
        
        metric.complete(success=False, error="Translation failed")
        
        assert metric.success is False
        assert metric.error == "Translation failed"


class TestExecutionMetrics:
    """Tests for ExecutionMetrics."""
    
    def test_execution_metrics_initialization(self):
        """Test ExecutionMetrics initialization."""
        start_time = time.time()
        metrics = ExecutionMetrics(start_time=start_time)
        
        assert metrics.start_time == start_time
        assert metrics.end_time is None
        assert metrics.duration_seconds is None
        assert metrics.files_processed == 0
        assert metrics.total_tool_calls == 0
        assert metrics.total_tokens == 0
    
    def test_execution_metrics_complete(self):
        """Test completing execution metrics."""
        start_time = time.time()
        metrics = ExecutionMetrics(start_time=start_time)
        
        # Add file metrics
        file_metric = FileProcessingMetric(
            file_path="test.md",
            language="en",
            start_time=time.time()
        )
        file_metric.complete(success=True)
        metrics.file_metrics.append(file_metric)
        
        time.sleep(0.01)
        metrics.complete()
        
        assert metrics.end_time is not None
        assert metrics.duration_seconds is not None
        assert metrics.files_processed == 1
        assert metrics.files_successful == 1
        assert metrics.files_failed == 0
    
    def test_execution_metrics_to_dict(self):
        """Test converting execution metrics to dictionary."""
        start_time = time.time()
        metrics = ExecutionMetrics(start_time=start_time)
        metrics.complete()
        
        metrics_dict = metrics.to_dict()
        
        assert "start_time" in metrics_dict
        assert "end_time" in metrics_dict
        assert "duration_seconds" in metrics_dict
        assert "files_processed" in metrics_dict
        assert "total_tool_calls" in metrics_dict
        assert "total_tokens" in metrics_dict
        assert "file_metrics" in metrics_dict


class TestMetricsCollector:
    """Tests for MetricsCollector.
    
    Requirements: 16.2, 16.4
    """
    
    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initialization."""
        collector = MetricsCollector()
        
        assert collector.metrics is not None
        assert collector.current_file_metric is None
        assert collector.current_tool_call is None
    
    def test_metrics_collector_file_processing(self):
        """Test tracking file processing metrics."""
        collector = MetricsCollector()
        
        collector.start_file_processing("test.md", "en")
        assert collector.current_file_metric is not None
        assert collector.current_file_metric.file_path == "test.md"
        assert collector.current_file_metric.language == "en"
        
        time.sleep(0.01)
        collector.end_file_processing(success=True)
        
        assert collector.current_file_metric is None
        assert len(collector.metrics.file_metrics) == 1
        assert collector.metrics.file_metrics[0].file_path == "test.md"
    
    def test_metrics_collector_tool_call(self):
        """Test tracking tool call metrics."""
        collector = MetricsCollector()
        
        collector.start_file_processing("test.md", "en")
        collector.start_tool_call("TranslateTool")
        
        assert collector.current_tool_call is not None
        assert collector.current_tool_call.tool_name == "TranslateTool"
        
        collector.end_tool_call(
            success=True,
            input_tokens=100,
            output_tokens=50
        )
        
        assert collector.current_tool_call is None
        assert len(collector.current_file_metric.tool_calls) == 1
        assert collector.current_file_metric.tool_calls[0].tool_name == "TranslateTool"
        assert collector.current_file_metric.tool_calls[0].input_tokens == 100
        assert collector.current_file_metric.tool_calls[0].output_tokens == 50
        
        collector.end_file_processing(success=True)
    
    def test_metrics_collector_error_recording(self):
        """Test recording errors in metrics."""
        collector = MetricsCollector()
        
        collector.record_error(
            error_type="TranslationError",
            error_message="Translation failed",
            context={"file": "test.md"}
        )
        
        assert len(collector.metrics.errors) == 1
        assert collector.metrics.errors[0]["error_type"] == "TranslationError"
        assert collector.metrics.errors[0]["error_message"] == "Translation failed"
    
    def test_metrics_collector_complete(self):
        """Test completing metrics collection."""
        collector = MetricsCollector()
        
        collector.start_file_processing("test.md", "en")
        collector.start_tool_call("TranslateTool")
        collector.end_tool_call(success=True, input_tokens=100, output_tokens=50)
        collector.end_file_processing(success=True)
        
        metrics = collector.complete()
        
        assert metrics.files_processed == 1
        assert metrics.files_successful == 1
        assert metrics.total_tool_calls == 1
        assert metrics.total_tokens == 150
    
    def test_metrics_collector_export_metrics(self, tmp_path):
        """Test exporting metrics to JSON file."""
        collector = MetricsCollector()
        
        collector.start_file_processing("test.md", "en")
        collector.end_file_processing(success=True)
        collector.complete()
        
        export_path = tmp_path / "metrics.json"
        collector.export_metrics(str(export_path))
        
        assert export_path.exists()
        
        with open(export_path) as f:
            data = json.load(f)
        
        assert "start_time" in data
        assert "files_processed" in data
        assert data["files_processed"] == 1


class TestLangChainTracer:
    """Tests for LangChainTracer.
    
    Requirements: 16.2, 16.4
    """
    
    def test_tracer_initialization(self):
        """Test LangChainTracer initialization."""
        collector = MetricsCollector()
        tracer = LangChainTracer(collector)
        
        assert tracer.metrics_collector == collector
        assert tracer.reasoning_steps == []
        assert tracer.current_step is None
    
    def test_tracer_agent_execution(self):
        """Test recording agent execution."""
        collector = MetricsCollector()
        tracer = LangChainTracer(collector)
        
        tracer.record_agent_start("TestAgent", "Test input")
        assert tracer.current_step is not None
        assert tracer.current_step["type"] == "agent_start"
        
        time.sleep(0.01)
        tracer.record_agent_end("Test output", success=True)
        
        assert tracer.current_step is None
        assert len(tracer.reasoning_steps) == 1
        assert tracer.reasoning_steps[0]["type"] == "agent_end"
        assert tracer.reasoning_steps[0]["success"] is True
    
    def test_tracer_tool_call(self):
        """Test recording tool calls."""
        collector = MetricsCollector()
        tracer = LangChainTracer(collector)
        
        tracer.record_tool_start("TranslateTool", {"content": "test"})
        assert len(tracer.reasoning_steps) == 1
        assert tracer.reasoning_steps[0]["type"] == "tool_call"
        
        tracer.record_tool_end(
            "TranslateTool",
            "translated content",
            success=True,
            input_tokens=100,
            output_tokens=50
        )
        
        assert tracer.reasoning_steps[0]["success"] is True
        assert tracer.reasoning_steps[0]["tokens"]["total"] == 150
    
    def test_tracer_reasoning_step(self):
        """Test recording reasoning steps."""
        collector = MetricsCollector()
        tracer = LangChainTracer(collector)
        
        tracer.record_reasoning_step(
            thought="I need to translate this file",
            action="Call TranslateTool",
            observation="Translation completed"
        )
        
        assert len(tracer.reasoning_steps) == 1
        assert tracer.reasoning_steps[0]["type"] == "reasoning"
        assert tracer.reasoning_steps[0]["thought"] == "I need to translate this file"
    
    def test_tracer_get_reasoning_steps(self):
        """Test retrieving reasoning steps."""
        collector = MetricsCollector()
        tracer = LangChainTracer(collector)
        
        tracer.record_reasoning_step("Thought", "Action", "Observation")
        tracer.record_reasoning_step("Thought 2", "Action 2", "Observation 2")
        
        steps = tracer.get_reasoning_steps()
        
        assert len(steps) == 2
        assert steps[0]["thought"] == "Thought"
        assert steps[1]["thought"] == "Thought 2"
    
    def test_tracer_export_reasoning_trace(self, tmp_path):
        """Test exporting reasoning trace to JSON file."""
        collector = MetricsCollector()
        tracer = LangChainTracer(collector)
        
        tracer.record_reasoning_step("Thought", "Action", "Observation")
        
        export_path = tmp_path / "trace.json"
        tracer.export_reasoning_trace(str(export_path))
        
        assert export_path.exists()
        
        with open(export_path) as f:
            data = json.load(f)
        
        assert "reasoning_steps" in data
        assert "total_steps" in data
        assert data["total_steps"] == 1


class TestMetricsIntegration:
    """Integration tests for metrics collection.
    
    Requirements: 16.2, 16.4
    """
    
    def test_full_metrics_collection_workflow(self):
        """Test complete metrics collection workflow."""
        collector = MetricsCollector()
        tracer = LangChainTracer(collector)
        
        # Simulate agent execution
        tracer.record_agent_start("GitBook Translator", "Translate docs")
        
        # Simulate file processing
        collector.start_file_processing("docs/intro.md", "en")
        tracer.record_tool_start("FetchGitHubFilesTool", {})
        tracer.record_tool_end("FetchGitHubFilesTool", "files fetched", input_tokens=50, output_tokens=25)
        
        tracer.record_tool_start("TranslateContentTool", {})
        tracer.record_tool_end("TranslateContentTool", "translated", input_tokens=100, output_tokens=150)
        
        collector.end_file_processing(success=True)
        
        # Simulate second file
        collector.start_file_processing("docs/guide.md", "en")
        tracer.record_tool_start("TranslateContentTool", {})
        tracer.record_tool_end("TranslateContentTool", "translated", input_tokens=80, output_tokens=120)
        collector.end_file_processing(success=True)
        
        tracer.record_agent_end("Translation completed", success=True)
        
        # Complete and verify
        metrics = collector.complete()
        
        assert metrics.files_processed == 2
        assert metrics.files_successful == 2
        assert metrics.total_tool_calls == 3
        assert metrics.total_tokens == 525  # 50+25+100+150+80+120
        assert len(tracer.get_reasoning_steps()) > 0
    
    def test_metrics_with_errors(self):
        """Test metrics collection with errors."""
        collector = MetricsCollector()
        
        collector.start_file_processing("docs/intro.md", "en")
        collector.start_tool_call("TranslateTool")
        collector.end_tool_call(success=False, error="Translation failed")
        collector.end_file_processing(success=False, error="File processing failed")
        
        collector.record_error("TranslationError", "Failed to translate", {"file": "intro.md"})
        
        metrics = collector.complete()
        
        assert metrics.files_processed == 1
        assert metrics.files_failed == 1
        assert len(metrics.errors) == 1
        assert metrics.errors[0]["error_type"] == "TranslationError"
