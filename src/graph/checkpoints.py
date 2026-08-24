from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.config.paths import LOGS_DIR
from src.db.sqlite_connection import get_checkpoint_connection

logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINT_DB_FILENAME = "vtd_checkpoints.sqlite"


def checkpoint_db_path(base_dir: Path | None = None) -> Path:
    directory = Path(base_dir) if base_dir else Path(LOGS_DIR) / "checkpoints"
    return directory / DEFAULT_CHECKPOINT_DB_FILENAME


def build_checkpointer(db_path: str | Path | None = None) -> Any | None:
    """Create a LangGraph SQLite checkpointer, or None when unavailable."""
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError:
        logger.warning("langgraph_checkpoint_sqlite_unavailable_checkpointer_disabled")
        return None

    resolved = checkpoint_db_path(Path(db_path)) if db_path else checkpoint_db_path()
    conn = get_checkpoint_connection(resolved)
    return SqliteSaver(conn)
