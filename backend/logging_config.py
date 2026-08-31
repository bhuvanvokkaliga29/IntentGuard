"""
IntentGuard — Production Structured Logging & Observability

Provides:
1. JSON structured logging formatter for centralized aggregation (Datadog, Loki, CloudWatch).
2. Trace / Correlation ID propagation across asynchronous tasks and requests.
3. Clean developer formatting when running in local development mode.
"""

import json
import logging
import sys
import contextvars
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variable for request correlation ID
correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("correlation_id", default=None)


class JSONStructuredFormatter(logging.Formatter):
    """Formats log records as structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": getattr(record, "environment", "production"),
            "module": record.module,
            "func_name": record.funcName,
            "line_no": record.lineno,
            "process_id": record.process,
            "thread_name": record.threadName,
        }

        # Attach correlation / trace ID if present
        trace_id = correlation_id_ctx.get()
        if trace_id:
            log_payload["trace_id"] = trace_id

        # Attach custom extra fields if provided in logger.info(..., extra={...})
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_payload.update(record.extra_data)

        # Attach exception info if present
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


def configure_logging(log_format: str = "json", log_level: str = "INFO", environment: str = "production") -> None:
    """Configure root logger with structured JSON or human-readable text."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if log_format.lower() == "json":
        handler.setFormatter(JSONStructuredFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))

    root_logger.addHandler(handler)
