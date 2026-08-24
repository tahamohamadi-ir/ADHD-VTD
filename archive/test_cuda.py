import os
import sys
from pathlib import Path

if sys.platform == "win32":
    # Add CUDA bin
    for v in ["v12.4", "v12.5", "v12.3", "v12.2", "v12.1", "v12.0"]:
        p = Path(f"C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\{v}\\bin")
        if p.exists():
            os.add_dll_directory(str(p))
            os.environ["PATH"] = str(p) + os.pathsep + os.environ["PATH"]
            print(f"Added CUDA DLL directory: {p}")
            break
    
    # Add llama_cpp lib
    llama_lib = Path(sys.prefix) / "Lib" / "site-packages" / "llama_cpp" / "lib"
    if llama_lib.exists():
        os.add_dll_directory(str(llama_lib))
        os.environ["PATH"] = str(llama_lib) + os.pathsep + os.environ["PATH"]
        print(f"Added llama_cpp DLL directory: {llama_lib}")

from llama_cpp import Llama, llama_supports_gpu_offload
print(f"GPU Offload Support: {llama_supports_gpu_offload()}")

print("Testing Llama load with CUDA...")
llm = Llama(model_path="models/generation/qwen2.5-coder-7b-instruct-q4_k_m.gguf", n_gpu_layers=-1, n_ctx=2048, verbose=True)
print("Model loaded successfully!")
