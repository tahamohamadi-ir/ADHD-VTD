from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.config.paths import DB_PATH, MODELS_DIR, RESULTS_DIR


@dataclass(frozen=True)
class AppSettings:
    project_name: str = "ADHD-VTD / VTD-Edge / PARS-SQL"
    runtime_mode: str = os.getenv("VTD_RUNTIME_MODE", "research")
    db_path: Path = Path(os.getenv("VTD_DB_PATH", str(DB_PATH)))
    models_dir: Path = Path(os.getenv("VTD_MODELS_DIR", str(MODELS_DIR)))
    results_dir: Path = Path(os.getenv("VTD_RESULTS_DIR", str(RESULTS_DIR)))
    default_model_path: str | None = os.getenv("VTD_DEFAULT_MODEL_PATH")
    sqlite_timeout_seconds: float = float(os.getenv("VTD_SQLITE_TIMEOUT", "10"))
    raw_retrieval_limit: int = int(os.getenv("VTD_RAW_RETRIEVAL_LIMIT", "100"))
    max_retries: int = int(os.getenv("VTD_MAX_RETRIES", "3"))
    random_seed: int = int(os.getenv("VTD_RANDOM_SEED", "42"))

    # Milestone gates
    milestone_1_min_ex_at_1: float = float(os.getenv("VTD_M1_MIN_EX_AT_1", "0.40"))
    milestone_1_min_valid_sql: float = float(os.getenv("VTD_M1_MIN_VALID_SQL", "0.70"))
    milestone_1_5_min_finglish_pass: float = float(os.getenv("VTD_M15_MIN_FINGLISH_PASS", "0.70"))
    milestone_1_5_required_unsafe_pass: float = 1.0


SETTINGS = AppSettings()
