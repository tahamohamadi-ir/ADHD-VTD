"""Timing utilities for VTD pipeline.

Provides context managers and decorators for measuring latency
of pipeline stages (normalization, schema linking, generation, etc.).
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Generator


@dataclass
class TimingRecord:
    """Holds the result of a timed operation."""
    stage: str
    elapsed_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@contextmanager
def measure_latency(stage: str = "unknown") -> Generator[TimingRecord, None, None]:
    """Context manager that measures wall-clock elapsed time in milliseconds.

    Usage::

        with measure_latency("schema_linking") as timing:
            result = schema_linker.link(question)
        print(f"{timing.stage}: {timing.elapsed_ms:.1f}ms")
    """
    record = TimingRecord(stage=stage)
    start = time.perf_counter()
    try:
        yield record
    finally:
        record.elapsed_ms = (time.perf_counter() - start) * 1000


def timed(stage: str | None = None) -> Callable:
    """Decorator that prints elapsed time for a function call.

    Usage::

        @timed("normalize")
        def normalize(text: str) -> str:
            ...
    """

    def decorator(fn: Callable) -> Callable:
        label = stage or fn.__qualname__

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                # Using print here to avoid circular import with logging module
                print(f"[TIMING] {label}: {elapsed:.1f}ms")

        return wrapper

    return decorator


class StageTimer:
    """Accumulator for multi-stage timing within a single pipeline run.

    Usage::

        timer = StageTimer()
        with timer.measure("normalize"):
            normalize(text)
        with timer.measure("schema_link"):
            link(question)
        print(timer.summary())
    """

    def __init__(self) -> None:
        self.records: list[TimingRecord] = []

    @contextmanager
    def measure(self, stage: str) -> Generator[TimingRecord, None, None]:
        record = TimingRecord(stage=stage)
        start = time.perf_counter()
        try:
            yield record
        finally:
            record.elapsed_ms = (time.perf_counter() - start) * 1000
            self.records.append(record)

    @property
    def total_ms(self) -> float:
        return sum(r.elapsed_ms for r in self.records)

    def summary(self) -> dict[str, float]:
        """Return a dict of {stage: elapsed_ms}."""
        return {r.stage: round(r.elapsed_ms, 2) for r in self.records}

    def summary_str(self) -> str:
        """Human-readable timing summary."""
        lines = [f"  {r.stage}: {r.elapsed_ms:.1f}ms" for r in self.records]
        lines.append(f"  TOTAL: {self.total_ms:.1f}ms")
        return "\n".join(lines)
