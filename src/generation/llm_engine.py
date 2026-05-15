from typing import Protocol, Any

class LLMEngine(Protocol):
    """Abstract interface for LLM generation engines."""
    
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from a prompt."""
        ...

    def generate_json(self, prompt: str, schema: dict | None = None, **kwargs: Any) -> str:
        """Generate JSON from a prompt, optionally constrained by a schema."""
        ...
