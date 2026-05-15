from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader

from src.core.query_ir import QueryIR

class PromptBuilder:
    """Builds prompts for LLM generation using Jinja2 templates."""

    def __init__(self, templates_dir: str | Path = "src/generation/prompts") -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def build_sql_generation_prompt(
        self,
        question: str,
        qir: QueryIR,
        schema: dict[str, Any],
        value_links: dict[str, str] | None = None,
        few_shot: list[dict[str, Any]] | None = None
    ) -> str:
        """
        Builds the main SQL generation prompt.
        """
        template = self.env.get_template("sql_generation.j2")
        
        # Serialize QIR to dict for easier templating if needed, but jinja can access properties
        return template.render(
            question=question,
            qir=qir,
            schema=schema,
            value_links=value_links or {},
            few_shot=few_shot or []
        )
