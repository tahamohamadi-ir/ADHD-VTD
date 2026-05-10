from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.core.types import (
    ExecutionResult,
    RouterDecision,
    SchemaLinkResult,
    ValidationResult,
    ValueLinkResult,
)


@runtime_checkable
class Normalizer(Protocol):
    def normalize(self, text: str) -> str:
        ...


@runtime_checkable
class IntentRouter(Protocol):
    def route(self, text: str) -> RouterDecision:
        ...


@runtime_checkable
class SchemaLinkerContract(Protocol):
    def link(self, question: str) -> SchemaLinkResult:
        ...


@runtime_checkable
class ValueLinkerContract(Protocol):
    def link_value(self, table: str, column: str, user_value: str) -> ValueLinkResult:
        ...


@runtime_checkable
class SQLValidator(Protocol):
    def validate(self, sql: str) -> ValidationResult:
        ...


@runtime_checkable
class ReadOnlyExecutor(Protocol):
    def execute(self, sql: str) -> ExecutionResult:
        ...


@runtime_checkable
class LocalLLM(Protocol):
    def generate(self, prompt: str) -> str:
        ...
