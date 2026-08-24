FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the light CI dependency set (no torch/chromadb/hazm/llama-cpp wheels).
COPY requirements-ci.txt ./
RUN pip install --no-cache-dir -r requirements-ci.txt

# Copy application code and frozen assets only; data/results/models stay outside.
COPY src ./src
COPY scripts ./scripts
COPY data/schema ./data/schema
COPY experiments ./experiments
COPY docs ./docs
COPY pyproject.toml VERSION README.md ./

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

# verify_artifact.py runs with the slim dependency set
# (run_benchmark.py needs pandas/openpyxl and stays out of this image).
CMD ["python", "scripts/verify_artifact.py", "--help"]
