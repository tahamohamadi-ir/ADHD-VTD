import json
import re
from typing import Any
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OutputParser:
    """Parses LLM output into structured data."""

    @staticmethod
    def extract_json(text: str) -> dict[str, Any] | None:
        """Extract JSON from LLM output with 3-stage fallback pipeline.

        Stage 1: Direct json.loads on stripped text
        Stage 2: Regex extraction of JSON from markdown fences or {...} blocks
        Stage 3: Raw SQL regex extraction as last resort
        """
        if not text or not text.strip():
            return None
        text = text.strip()

        # Stage 1: Direct parse
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        # Stage 2: Extract JSON from markdown fences or find {...} block
        # 2a: Try ```json ... ``` fence
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                pass

        # 2b: Find outermost { ... } containing "sql"
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                result = json.loads(candidate)
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, ValueError):
                pass

            # 2c: Try to fix common issues (trailing comma, single quotes)
            cleaned = candidate.replace("'", '"')
            cleaned = re.sub(r",\s*}", "}", cleaned)
            cleaned = re.sub(r",\s*]", "]", cleaned)
            try:
                result = json.loads(cleaned)
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, ValueError):
                pass

        # Stage 3: Raw SQL extraction fallback
        sql_match = re.search(
            r"((?:SELECT|WITH)\s+.+?(?:FROM\s+\w+).+?)(?:;\s*$|;\s*\n|\n\n|```|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if sql_match:
            extracted_sql = sql_match.group(1).strip().rstrip(";")
            logger.warning(
                f"JSON parse failed, fell back to raw SQL extraction: {extracted_sql[:80]}..."
            )
            return {
                "sql": extracted_sql,
                "explanation": "Auto-extracted from raw model output (JSON parse failed).",
                "needs_clarification": False,
                "_fallback_extraction": True,
            }

        logger.error(f"Failed to parse JSON and no SQL found in output: {text[:200]}...")
        return None

    @staticmethod
    def extract_thought_process(parsed: dict[str, Any] | None) -> str | None:
        """Extract thought_process field from parsed CoT output."""
        if parsed and isinstance(parsed, dict):
            return parsed.get("thought_process")
        return None

    @staticmethod
    def extract_sql(text: str) -> str | None:
        """Extract SQL from text."""
        text = text.strip()
        # Look for markdown sql fences
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # If no fences, and it starts with SELECT/WITH, return it
        upper = text.upper()
        if upper.startswith("SELECT") or upper.startswith("WITH"):
            return text

        return None
