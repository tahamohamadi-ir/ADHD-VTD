import json
import os
import sys
from pathlib import Path
from typing import Any

# Windows-specific CUDA DLL path handling
if sys.platform == "win32":
    # Try to find CUDA path from environment or common installation locations
    cuda_path = os.environ.get("CUDA_PATH")
    if not cuda_path:
        # Check standard installation paths for CUDA 12.x
        for v in ["v12.4", "v12.5", "v12.3", "v12.2", "v12.1", "v12.0"]:
            p = Path(f"C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\{v}")
            if p.exists():
                cuda_path = str(p)
                break
    
    if cuda_path:
        cuda_bin = Path(cuda_path) / "bin"
        if cuda_bin.exists():
            try:
                # Add to DLL search path (Python 3.8+)
                os.add_dll_directory(str(cuda_bin))
                # Add to PATH for older dependencies or C-based loaders
                os.environ["PATH"] = str(cuda_bin) + os.pathsep + os.environ["PATH"]
            except Exception:
                pass

    # Also add the internal llama_cpp/lib directory
    try:
        # Try to locate the package directory
        import importlib.util
        spec = importlib.util.find_spec("llama_cpp")
        if spec and spec.origin:
            pkg_root = Path(spec.origin).parent
            lib_dir = pkg_root / "lib"
            if lib_dir.exists():
                os.add_dll_directory(str(lib_dir))
                os.environ["PATH"] = str(lib_dir) + os.pathsep + os.environ["PATH"]
    except Exception:
        pass

from src.generation.llm_engine import LLMEngine
from src.utils.logging import get_logger

logger = get_logger(__name__)

class LocalLLM(LLMEngine):
    """Local LLM Engine using llama-cpp-python."""

    def __init__(
        self,
        model_path: str | Path,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        seed: int = 42,
        temperature: float = 0.0,
        top_p: float = 1.0,
        verbose: bool = False
    ) -> None:
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError("llama-cpp-python is required to use LocalLLM")
            
        self.model_path = str(model_path)
        self.seed = seed
        self.temperature = temperature
        self.top_p = top_p
        
        logger.info(f"Loading local LLM from {self.model_path} (n_ctx={n_ctx})")
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            seed=seed,
            verbose=verbose,
        )

    def generate(self, prompt: str, **kwargs: Any) -> str:
        temp = kwargs.get("temperature", self.temperature)
        top_p = kwargs.get("top_p", self.top_p)
        max_tokens = kwargs.get("max_tokens", 1024)
        stop = kwargs.get("stop", [])
        
        response = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temp,
            top_p=top_p,
            stop=stop,
            echo=False,
            stream=False
        )
        if isinstance(response, dict):
            return response["choices"][0]["text"]
        return ""

    def generate_json(self, prompt: str, schema: dict | None = None, **kwargs: Any) -> str:
        temp = kwargs.get("temperature", self.temperature)
        top_p = kwargs.get("top_p", self.top_p)
        max_tokens = kwargs.get("max_tokens", 1024)
        stop = kwargs.get("stop", [])
        
        from llama_cpp import LlamaGrammar
        
        grammar = None
        if schema:
            grammar = LlamaGrammar.from_json_schema(json.dumps(schema))
        elif kwargs.get("enforce_json", True):
            # A strict schema specifically for the SQL JSON response
            default_schema = {
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "explanation": {"type": "string"},
                    "needs_clarification": {"type": "boolean"}
                },
                "required": ["sql", "explanation", "needs_clarification"]
            }
            grammar = LlamaGrammar.from_json_schema(json.dumps(default_schema))

        response = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temp,
            top_p=top_p,
            grammar=grammar,
            stop=stop,
            echo=False,
            stream=False
        )
        if isinstance(response, dict):
            return response["choices"][0]["text"]
        return ""
