import json
import re
from typing import Any
from src.utils.logging import get_logger

logger = get_logger(__name__)

class OutputParser:
    """Parses LLM output into structured data."""

    @staticmethod
    def extract_json(text: str) -> dict[str, Any] | None:
        """Extract JSON from text, even if wrapped in markdown fences."""
        text = text.strip()
        
        # Try finding json block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback to finding first { and last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = text[start : end + 1]
            else:
                json_str = text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
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
