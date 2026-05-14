"""PARS-SQL / VTD-Edge CLI entry point.

Usage:
    python main.py normalize "میانگین افسردگی دانشجوها"
    python main.py classify "تعداد دانشجوهای افسرده چقدره?"
    python main.py link "میانگین نمره افسردگی زنان"
    python main.py validate "SELECT AVG(phq9_score) FROM student_depression"
    python main.py smoke-test
    python main.py info
"""
from __future__ import annotations

import json
import sys

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="vtd",
    help="PARS-SQL / VTD-Edge — Persian Text-to-SQL CLI",
    add_completion=False,
)
console = Console()


@app.command()
def normalize(question: str = typer.Argument(..., help="Persian question to normalize")):
    """Normalize a Persian question through the full NLU pipeline."""
    from src.nlu.persian_normalizer import PersianNormalizer

    result = PersianNormalizer().normalize(question)
    rprint(f"[bold]Original:[/bold]   {result.original}")
    rprint(f"[bold]Normalized:[/bold] {result.normalized}")
    if result.matched_colloquials:
        rprint(f"[bold]Colloquials:[/bold] {json.dumps(result.matched_colloquials, ensure_ascii=False, indent=2)}")


@app.command()
def classify(question: str = typer.Argument(..., help="Question to classify")):
    """Classify the intent of a Persian question."""
    from src.nlu.intent_classifier import IntentClassifier

    decision = IntentClassifier().classify(question)
    table = Table(title="Intent Classification")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Intent", decision.intent)
    table.add_row("Confidence", f"{decision.confidence:.2f}")
    table.add_row("Generate SQL", str(decision.should_generate_sql))
    table.add_row("Action", decision.expected_action)
    table.add_row("Reasons", "\n".join(decision.reasons) if decision.reasons else "—")
    console.print(table)


@app.command()
def link(question: str = typer.Argument(..., help="Question to schema-link")):
    """Run schema linking on a Persian question."""
    from src.schema.schema_linker import SchemaLinker

    result = SchemaLinker().link(question)
    table = Table(title="Schema Linking Result")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Tables", ", ".join(result.tables) or "—")
    table.add_row("Columns", "\n".join(result.columns) or "—")
    table.add_row("Metrics", ", ".join(result.metrics) or "—")
    table.add_row("Join Hints", "\n".join(result.join_hints) or "—")
    table.add_row("Confidence", f"{result.confidence:.3f}")
    table.add_row("Unresolved", ", ".join(result.unresolved_terms) or "—")
    console.print(table)


@app.command()
def validate(sql: str = typer.Argument(..., help="SQL to validate")):
    """Validate SQL through safety and schema validators."""
    from src.sql_validation.safety_validator import SQLSafetyValidator
    from src.sql_validation.schema_validator import SQLSchemaValidator

    safety_result = SQLSafetyValidator().validate(sql)
    schema_result = SQLSchemaValidator().validate(sql)

    table = Table(title="SQL Validation")
    table.add_column("Validator", style="cyan")
    table.add_column("OK", style="green")
    table.add_column("Issues", style="red")
    table.add_row("Safety", "✅" if safety_result.ok else "❌", "\n".join(safety_result.messages()) or "—")
    table.add_row("Schema", "✅" if schema_result.ok else "❌", "\n".join(schema_result.messages()) or "—")
    console.print(table)


@app.command(name="extract-terms")
def extract_terms(question: str = typer.Argument(..., help="Question to extract terms from")):
    """Extract semantic terms from a Persian question."""
    from src.nlu.term_extractor import TermExtractor

    result = TermExtractor().extract(question)
    rprint(f"[bold]Normalized:[/bold] {result.normalized}")
    rprint(f"[bold]Terms:[/bold]      {result.terms}")
    rprint(f"[bold]Bigrams:[/bold]    {result.bigrams}")
    rprint(f"[bold]Trigrams:[/bold]   {result.trigrams}")
    rprint(f"[bold]Numbers:[/bold]    {result.numbers}")


@app.command(name="smoke-test")
def smoke_test():
    """Run a quick smoke test of all core components."""
    from src.nlu.persian_normalizer import PersianNormalizer
    from src.nlu.intent_classifier import IntentClassifier
    from src.nlu.term_extractor import TermExtractor
    from src.schema.schema_linker import SchemaLinker
    from src.sql_validation.safety_validator import SQLSafetyValidator
    from src.sql_validation.sql_rewriter import SQLRewriter

    test_q = "میانگین نمره افسردگی دانشجوهای زن چقدره?"
    rprint(f"\n[bold yellow]Test question:[/bold yellow] {test_q}\n")

    steps = [
        ("Normalize", lambda: PersianNormalizer().normalize(test_q).normalized),
        ("Terms", lambda: TermExtractor().extract_terms(test_q)),
        ("Intent", lambda: IntentClassifier().classify(test_q).intent),
        ("Schema Link", lambda: SchemaLinker().link(test_q).tables),
        ("Safety", lambda: SQLSafetyValidator().validate("SELECT AVG(phq9_score) FROM student_depression").ok),
        ("Rewriter", lambda: SQLRewriter().rewrite("```sql\nSELECT * FROM student_depression;\n```")),
    ]

    all_ok = True
    for name, fn in steps:
        try:
            result = fn()
            rprint(f"  ✅ {name}: {result}")
        except Exception as exc:
            rprint(f"  ❌ {name}: {exc}")
            all_ok = False

    rprint(f"\n{'✅ All components OK!' if all_ok else '❌ Some components failed.'}\n")


@app.command()
def info():
    """Display project configuration and paths."""
    from src.config.paths import PROJECT_ROOT, DB_PATH, SCHEMA_DIR
    from src.config.settings import SETTINGS

    table = Table(title="VTD Project Info")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Project Root", str(PROJECT_ROOT))
    table.add_row("DB Path", str(DB_PATH))
    table.add_row("Schema Dir", str(SCHEMA_DIR))
    table.add_row("Runtime Mode", SETTINGS.runtime_mode)
    table.add_row("SQLite Timeout", f"{SETTINGS.sqlite_timeout_seconds}s")
    table.add_row("Max Retries", str(SETTINGS.max_retries))
    console.print(table)


if __name__ == "__main__":
    app()
