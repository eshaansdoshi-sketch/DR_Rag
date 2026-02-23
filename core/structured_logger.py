"""Structured JSON Logging System.

Provides:
  - StructuredFormatter: JSON log formatter with standard fields
  - setup_logging(): configure root logger for structured output
  - log_event(): convenience helper to emit structured log events

Standard fields on every log line:
  timestamp, level, logger, message, run_id, iteration, subtopic,
  event_type, latency_ms, retry_count

Safety:
  - Never logs full LLM prompts unless DEBUG level is enabled
  - Non-blocking (standard logging module — buffered I/O)
  - No sensitive data (API keys, tokens) in log output
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Event types for machine-parseable categorisation
# ---------------------------------------------------------------------------
class EventType:
    # API calls
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_SUCCESS = "llm_call_success"
    LLM_CALL_ERROR = "llm_call_error"
    SEARCH_CALL_START = "search_call_start"
    SEARCH_CALL_SUCCESS = "search_call_success"
    SEARCH_CALL_ERROR = "search_call_error"

    # Caching
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_PUT = "cache_put"

    # Rate limiting & retries
    RATE_LIMIT_WAIT = "rate_limit_wait"
    RETRY_ATTEMPT = "retry_attempt"
    RETRY_EXHAUSTED = "retry_exhausted"

    # Orchestrator lifecycle
    RUN_START = "run_start"
    RUN_COMPLETE = "run_complete"
    ITERATION_START = "iteration_start"
    ITERATION_COMPLETE = "iteration_complete"

    # Evaluation & planning
    EVALUATION_COMPLETE = "evaluation_complete"
    PLAN_MUTATION = "plan_mutation"
    BUDGET_EXCEEDED = "budget_exceeded"
    SUBTOPIC_FAILURE = "subtopic_failure"


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------
class StructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON.

    Merges any ``extra`` dict keys into the top-level JSON object so
    callers can attach arbitrary structured fields via ``logger.info(..., extra={...})``.
    """

    # Keys injected by the logging module itself — never forward these
    _RESERVED = frozenset({
        "name", "msg", "args", "created", "relativeCreated",
        "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "filename", "module", "pathname", "thread", "threadName",
        "process", "processName", "taskName", "message", "msecs",
        "levelname", "levelno",
    })

    def format(self, record: logging.LogRecord) -> str:
        # Build base payload
        payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.") + f"{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge caller-provided structured fields
        for key, val in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = val

        # Attach exception info if present
        if record.exc_info and record.exc_info[1]:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Setup helper
# ---------------------------------------------------------------------------
_configured = False


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with structured JSON output.

    Safe to call multiple times — only configures once.
    """
    global _configured
    if _configured:
        return
    _configured = True

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Allow override from env
    env_level = os.getenv("LOG_LEVEL")
    if env_level:
        log_level = getattr(logging, env_level.upper(), log_level)

    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove any existing handlers (e.g. basicConfig defaults)
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)


# ---------------------------------------------------------------------------
# Convenience helper
# ---------------------------------------------------------------------------
def log_event(
    logger: logging.Logger,
    level: int,
    event_type: str,
    message: str,
    *,
    run_id: Optional[str] = None,
    iteration: Optional[int] = None,
    subtopic: Optional[str] = None,
    latency_ms: Optional[float] = None,
    retry_count: Optional[int] = None,
    **extra: Any,
) -> None:
    """Emit a structured log event with standard fields.

    Example::

        log_event(logger, logging.INFO, EventType.LLM_CALL_SUCCESS,
                  "Groq call completed", run_id="abc123", latency_ms=342.1)
    """
    fields: Dict[str, Any] = {"event_type": event_type}
    if run_id is not None:
        fields["run_id"] = run_id
    if iteration is not None:
        fields["iteration"] = iteration
    if subtopic is not None:
        fields["subtopic"] = subtopic
    if latency_ms is not None:
        fields["latency_ms"] = round(latency_ms, 2)
    if retry_count is not None:
        fields["retry_count"] = retry_count
    fields.update(extra)

    logger.log(level, message, extra=fields)
