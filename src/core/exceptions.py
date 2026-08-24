"""VTD exception hierarchy.

Every module-specific exception inherits from VTDException so that
top-level handlers can catch the entire family with a single clause.
"""

from __future__ import annotations


class VTDException(Exception):
    """Base exception for all VTD / PARS-SQL errors."""

    def __init__(self, message: str = "", *, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


# ── Schema ──────────────────────────────────────────────────────────
class SchemaNotFoundError(VTDException):
    """Raised when a referenced table or column does not exist in the frozen schema."""


class SchemaColumnNotFoundError(SchemaNotFoundError):
    """Raised when a specific column cannot be found in a known table."""


class SchemaTableNotFoundError(SchemaNotFoundError):
    """Raised when a table name cannot be resolved in the schema registry."""


# ── SQL Safety ──────────────────────────────────────────────────────
class UnsafeSQLError(VTDException):
    """Raised when generated SQL contains forbidden/unsafe operations."""


class SQLValidationError(VTDException):
    """Raised when SQL fails syntax, schema, or semantic validation."""


class SQLExecutionError(VTDException):
    """Raised when a read-only SQL execution fails at the DB layer."""


# ── NLU / Query Understanding ──────────────────────────────────────
class AmbiguousQueryError(VTDException):
    """Raised when the user question is too vague to produce reliable SQL."""


class UnsupportedQueryError(VTDException):
    """Raised when the query type is not supported by the current pipeline."""


# ── Generation ──────────────────────────────────────────────────────
class GenerationError(VTDException):
    """Raised when LLM generation fails or returns unparseable output."""


class OutputParseError(GenerationError):
    """Raised when the LLM output cannot be parsed into the expected format."""


# ── Retrieval / CAG ─────────────────────────────────────────────────
class RetrievalError(VTDException):
    """Raised when the retrieval/CAG pipeline encounters an error."""


# ── Configuration ───────────────────────────────────────────────────
class ConfigurationError(VTDException):
    """Raised when a required configuration value is missing or invalid."""


# ── Reliability / Abstention ────────────────────────────────────────
class ReliabilityGateError(VTDException):
    """Raised when the reliability gate decides to abstain."""


# ── Data / Dataset ──────────────────────────────────────────────────
class DatasetError(VTDException):
    """Raised when dataset loading or validation fails."""
