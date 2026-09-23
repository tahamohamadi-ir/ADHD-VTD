#!/usr/bin/env bash
# Cloud Agent bootstrap for PARS-SQL / VTD-Edge.
# Idempotent: safe to re-run against a cached/snapshotted VM.
set -euo pipefail

cd "$(dirname "$0")/.."

# --- System build dependencies -------------------------------------------------
# python3.12-venv provides ensurepip; build-essential/cmake are needed to compile
# native wheels such as llama-cpp-python. Skipped automatically if unavailable.
if command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
else
  SUDO=""
fi

if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  $SUDO apt-get update -qq || true
  $SUDO apt-get install -y -qq python3.12-venv build-essential cmake || true
fi

# --- Python virtual environment ------------------------------------------------
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate

python -m pip install --upgrade pip

# Full research stack (NLU, retrieval, local LLM, evaluation, lint + tests).
pip install -r requirements.txt

echo "PARS-SQL environment ready. Activate with: source .venv/bin/activate"
