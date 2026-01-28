"""Monitoring and observability utilities for the Translation Agent."""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class MetricType(Enum):
    """Types of metrics to track."""
    
    EXECUTION_TIME = "execution_time"
    TOOL_CALL = "tool_call"
    TOKEN_USAGE = "token_usage"
    ERROR = "error"
    FILE_PROCESSED = "file_processed"


@dataclass
class TokenUsage:
    """Token usage information from LLM calls."""
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __post_init__(self):
        """Validate token counts."""
        if self.total_tokens == 0 and (self.prompt_tokens > 0 or self.completion_tokens > 0):
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class ToolCallMetric:
    """Metric for a single tool call."""
    
    tool_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    
    def complete(self, success: bool = True, error: Optional[str] = None):
        """Mark the tool call as complete.
        
        Args:
            success: Whether the tool call succeeded
            error: Error message if failed
        """
        self.end_time = time.time()
        self.duration_seconds = self.end_time - self.start_time
        self.success = success
        self.error = error


@dataclass
class FileProcessingMetric:
    """Metric for processing a single file."""
    
    file_path: str
    language: str
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    tool_calls: List[ToolCallMetric] = field(default_factory=list)
    total_tokens: int = 0
    
    def complete(self, success: bool = True, error: Optional[str] = None):
        """Mark file processing as complete.
        
        Args:
            success: Whether processing succeeded
            error: Error message if failed
        """
        self.end_time = time.time()
        self.duration_seconds = self.end_time - self.start_time
        self.success = success
        self.error = error
        
        # Calculate total tokens from tool calls
        self.total_tokens = sum(
            call.input_tokens + call.output_tokens 
            for call in self.tool_calls
        )


@dataclass
class ExecutionMetrics:
    """Aggregated execution metrics for the entire run."""
    
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    
    # File processing metrics
    files_processed: int = 0
    files_successful: int = 0
    files_failed: int = 0
    
    # Tool call metrics
    total_tool_calls: int = 0
    tool_calls_by_name: Dict[str, int] = field(default_factory=dict)
    
    # Token usage metrics
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    
    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Detailed metrics
    file_metrics: List[FileProcessingMetric] = field(default_factory=list)
    
    def complete(self):
        """Mark execution as complete and calculate final metrics."""
        self.end_time = time.time()
        self.duration_seconds = self.end_time - self.start_time
        
        # Aggregate file metrics
        self.files_processed = len(self.file_metrics)
        self.files_successful = sum(1 for m in self.file_metrics if m.success)
        self.files_failed = self.files_processed - self.files_successful
        
        # Aggregate tool call metrics
        for file_metric in self.file_metrics:
            self.total_tool_calls += len(file_metric.tool_calls)
            self.total_tokens += file_metric.total_tokens
            
            for tool_call in file_metric.tool_calls:
                tool_name = tool_call.tool_name
                self.tool_calls_by_name[tool_name] = self.tool_calls_by_name.get(tool_name, 0) + 1
                self.total_prompt_tokens += tool_call.input_tokens
                self.total_completion_tokens += tool_call.output_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization.
        
        Returns:
            Dictionary representation of metrics
        """
        return {
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "files_processed": self.files_processed,
            "files_successful": self.files_successful,
            "files_failed": self.files_failed,
            "total_tool_calls": self.total_tool_calls,
            "tool_calls_by_name": self.tool_calls_by_name,
            "total_tokens": self.total_tokens,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "errors": self.errors,
            "file_metrics": [
                {
                    "file_path": m.file_path,
                    "language": m.language,
                    "duration_seconds": m.duration_seconds,
                    "success": m.success,
                    "error": m.error,
                    "tool_calls_count": len(m.tool_calls),
                    "total_tokens": m.total_tokens,
                }
                for m in self.file_metrics
            ]
        }


class MetricsCollector:
    """Collects and aggregates metrics during agent execution.
    
    Requirements: 16.2, 16.4
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        self.metrics = ExecutionMetrics(start_time=time.time())
        self.current_file_metric: Optional[FileProcessingMetric] = None
        self.current_tool_call: Optional[ToolCallMetric] = None
    
    def start_file_processing(self, file_path: str, language: str) -> None:
        """Start tracking metrics for a file.
        
        Args:
            file_path: Path to the file being processed
            language: Target language for translation
        """
        self.current_file_metric = FileProcessingMetric(
            file_path=file_path,
            language=language,
            start_time=time.time()
        )
    
    def end_file_processing(self, success: bool = True, error: Optional[str] = None) -> None:
        """End tracking metrics for a file.
        
        Args:
            success: Whether file processing succeeded
            error: Error message if failed
        """
        if self.current_file_metric:
            self.current_file_metric.complete(success=success, error=error)
            self.metrics.file_metrics.append(self.current_file_metric)
            self.current_file_metric = None
    
    def start_tool_call(self, tool_name: str) -> None:
        """Start tracking metrics for a tool call.
        
        Args:
            tool_name: Name of the tool being called
        """
        self.current_tool_call = ToolCallMetric(
            tool_name=tool_name,
            start_time=time.time()
        )
    
    def end_tool_call(
        self,
        success: bool = True,
        error: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> None:
        """End tracking metrics for a tool call.
        
        Args:
            success: Whether tool call succeeded
            error: Error message if failed
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
        """
        if self.current_tool_call:
            self.current_tool_call.input_tokens = input_tokens
            self.current_tool_call.output_tokens = output_tokens
            self.current_tool_call.complete(success=success, error=error)
            
            if self.current_file_metric:
                self.current_file_metric.tool_calls.append(self.current_tool_call)
            
            self.current_tool_call = None
    
    def record_error(self, error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Record an error that occurred during execution.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Additional context about the error
        """
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }
        self.metrics.errors.append(error_entry)
    
    def complete(self) -> ExecutionMetrics:
        """Complete metrics collection and return final metrics.
        
        Returns:
            ExecutionMetrics with all collected data
        """
        self.metrics.complete()
        return self.metrics
    
    def get_metrics(self) -> ExecutionMetrics:
        """Get current metrics without completing collection.
        
        Returns:
            Current ExecutionMetrics
        """
        return self.metrics
    
    def export_metrics(self, file_path: str) -> None:
        """Export metrics to a JSON file.
        
        Args:
            file_path: Path to export metrics to
        """
        metrics_dict = self.metrics.to_dict()
        with open(file_path, 'w') as f:
            json.dump(metrics_dict, f, indent=2)


class LangChainTracer:
    """Tracer for LangChain agent execution.
    
    Integrates with LangChain's callback system to track:
    - Agent reasoning steps
    - Tool calls and results
    - Token usage
    - Execution flow
    
    Requirements: 16.2, 16.4
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize the tracer.
        
        Args:
            metrics_collector: MetricsCollector instance for recording metrics
        """
        self.metrics_collector = metrics_collector
        self.reasoning_steps: List[Dict[str, Any]] = []
        self.current_step: Optional[Dict[str, Any]] = None
    
    def record_agent_start(self, agent_name: str, input_text: str) -> None:
        """Record the start of agent execution.
        
        Args:
            agent_name: Name of the agent
            input_text: Input text to the agent
        """
        self.current_step = {
            "type": "agent_start",
            "agent": agent_name,
            "input": input_text,
            "timestamp": datetime.now().isoformat(),
            "start_time": time.time()
        }
    
    def record_agent_end(self, output_text: str, success: bool = True) -> None:
        """Record the end of agent execution.
        
        Args:
            output_text: Output from the agent
            success: Whether execution succeeded
        """
        if self.current_step:
            self.current_step["type"] = "agent_end"
            self.current_step["output"] = output_text
            self.current_step["success"] = success
            self.current_step["end_time"] = time.time()
            self.current_step["duration"] = (
                self.current_step["end_time"] - self.current_step["start_time"]
            )
            self.reasoning_steps.append(self.current_step)
            self.current_step = None
    
    def record_tool_start(self, tool_name: str, tool_input: Dict[str, Any]) -> None:
        """Record the start of a tool call.
        
        Args:
            tool_name: Name of the tool
            tool_input: Input to the tool
        """
        self.metrics_collector.start_tool_call(tool_name)
        
        step = {
            "type": "tool_call",
            "tool": tool_name,
            "input": tool_input,
            "timestamp": datetime.now().isoformat(),
            "start_time": time.time()
        }
        self.reasoning_steps.append(step)
    
    def record_tool_end(
        self,
        tool_name: str,
        tool_output: Any,
        success: bool = True,
        error: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> None:
        """Record the end of a tool call.
        
        Args:
            tool_name: Name of the tool
            tool_output: Output from the tool
            success: Whether tool call succeeded
            error: Error message if failed
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
        """
        self.metrics_collector.end_tool_call(
            success=success,
            error=error,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        
        # Update the last tool call step
        if self.reasoning_steps and self.reasoning_steps[-1]["type"] == "tool_call":
            self.reasoning_steps[-1]["output"] = tool_output
            self.reasoning_steps[-1]["success"] = success
            self.reasoning_steps[-1]["error"] = error
            self.reasoning_steps[-1]["end_time"] = time.time()
            self.reasoning_steps[-1]["duration"] = (
                self.reasoning_steps[-1]["end_time"] - self.reasoning_steps[-1]["start_time"]
            )
            self.reasoning_steps[-1]["tokens"] = {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            }
    
    def record_reasoning_step(self, thought: str, action: str, observation: str) -> None:
        """Record a reasoning step (Thought/Action/Observation).
        
        Args:
            thought: The agent's thought
            action: The action taken
            observation: The observation from the action
        """
        step = {
            "type": "reasoning",
            "thought": thought,
            "action": action,
            "observation": observation,
            "timestamp": datetime.now().isoformat()
        }
        self.reasoning_steps.append(step)
    
    def get_reasoning_steps(self) -> List[Dict[str, Any]]:
        """Get all recorded reasoning steps.
        
        Returns:
            List of reasoning steps
        """
        return self.reasoning_steps
    
    def export_reasoning_trace(self, file_path: str) -> None:
        """Export reasoning trace to a JSON file.
        
        Args:
            file_path: Path to export trace to
        """
        trace_data = {
            "timestamp": datetime.now().isoformat(),
            "reasoning_steps": self.reasoning_steps,
            "total_steps": len(self.reasoning_steps)
        }
        with open(file_path, 'w') as f:
            json.dump(trace_data, f, indent=2)
