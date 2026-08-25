from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    location: str | None = None


@dataclass(frozen=True)
class RepairHint:
    action: str
    target: str
    suggestion: str
    confidence: float = 0.5


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    normalized_sql: str | None = None
    repair_hints: tuple[RepairHint, ...] = ()

    @classmethod
    def pass_(cls, normalized_sql: str | None = None) -> "ValidationResult":
        return cls(True, [], normalized_sql)

    @classmethod
    def fail(cls, code: str, message: str, location: str | None = None) -> "ValidationResult":
        return cls(False, [ValidationIssue(code, message, "error", location)])

    def add(self, issue: ValidationIssue) -> "ValidationResult":
        return ValidationResult(False, [*self.issues, issue], self.normalized_sql, self.repair_hints)

    def messages(self) -> list[str]:
        return [i.message for i in self.issues]

    def with_hints(self, hints: tuple[RepairHint, ...]) -> "ValidationResult":
        merged = tuple(dict.fromkeys((*self.repair_hints, *hints)))
        return ValidationResult(self.ok, self.issues, self.normalized_sql, merged)
