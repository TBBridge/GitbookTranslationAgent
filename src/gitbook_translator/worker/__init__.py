"""Local worker adapter for the deterministic translation pipeline."""

from gitbook_translator.worker.config import load_worker_config, parse_worker_config
from gitbook_translator.worker.models import WorkerCapabilities, WorkerConfig

__all__ = [
    "WorkerCapabilities",
    "WorkerConfig",
    "load_worker_config",
    "parse_worker_config",
]
