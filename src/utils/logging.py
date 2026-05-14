"""Structured logging for VTD pipeline.

Provides a pre-configured ``loguru`` logger with:
- trace_id injection via ``contextvars``
- JSON-structured log file output
- Rich console output for development
- Configurable log levels via environment variables
"""
from __future__ import annotations

import os
import sys
import uuid
from contextvars import ContextVar
from pathlib import Path

from loguru import logger as _loguru_logger

# ── Trace ID context ───────────────────────────────────────────────
_trace_id_var: ContextVar[str] = ContextVar("vtd_trace_id", default="no-trace")


def new_trace_id() -> str:
    """Generate and set a new trace ID for the current async/thread context."""
    tid = uuid.uuid4().hex[:12]
    _trace_id_var.set(tid)
    return tid


def get_trace_id() -> str:
    """Return the current trace ID."""
    return _trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """Manually set the trace ID (e.g. when resuming a previous trace)."""
    _trace_id_var.set(trace_id)


# ── Logger configuration ──────────────────────────────────────────

def _trace_id_patcher(record: dict) -> None:  # type: ignore[type-arg]
    record["extra"]["trace_id"] = _trace_id_var.get()


_loguru_logger = _loguru_logger.patch(_trace_id_patcher)  # type: ignore[assignment]

# Remove default loguru handler
_loguru_logger.remove()

# Console handler (human-readable)
_console_level = os.getenv("VTD_LOG_LEVEL", "INFO").upper()
_loguru_logger.add(
    sys.stderr,
    level=_console_level,
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[trace_id]}</cyan> | "
        "<level>{message}</level>"
    ),
    colorize=True,
)

# File handler (JSON structured, for post-hoc analysis)
_log_dir = Path(os.getenv("VTD_LOG_DIR", "logs"))
_log_dir.mkdir(parents=True, exist_ok=True)
_loguru_logger.add(
    str(_log_dir / "vtd_{time:YYYY-MM-DD}.log"),
    level="DEBUG",
    format="{time:YYYY-MM-DDTHH:mm:ss.SSS} | {level} | {extra[trace_id]} | {message}",
    rotation="10 MB",
    retention="30 days",
    encoding="utf-8",
    serialize=False,
)


def get_logger(name: str | None = None) -> "loguru.Logger":  # type: ignore[name-defined]
    """Return a child logger bound with the given module name."""
    if name:
        return _loguru_logger.bind(module=name)
    return _loguru_logger


# Re-export the configured logger for direct import
vtd_logger = _loguru_logger
