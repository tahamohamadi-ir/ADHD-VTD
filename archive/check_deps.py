import ctypes
import os
from pathlib import Path

cuda_bin = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin"
dlls = ["cudart64_12.dll", "cublas64_12.dll", "cublasLt64_12.dll"]

print(f"Checking CUDA DLLs in {cuda_bin}...")
for dll in dlls:
    path = Path(cuda_bin) / dll
    if not path.exists():
        print(f"MISSING: {path}")
        continue
    try:
        ctypes.CDLL(str(path))
        print(f"SUCCESS: Loaded {dll}")
    except Exception as e:
        print(f"FAIL: {dll} - {e}")

print("\nChecking llama.dll dependencies...")
llama_dll = r"D:\Project\ADHD-VTD\.venv\Lib\site-packages\llama_cpp\lib\llama.dll"
if os.path.exists(llama_dll):
    os.add_dll_directory(cuda_bin)
    try:
        ctypes.CDLL(llama_dll)
        print("SUCCESS: Loaded llama.dll")
    except Exception as e:
        print(f"FAIL: llama.dll - {e}")
else:
    print(f"MISSING: {llama_dll}")
