from __future__ import annotations

import sys
from pathlib import Path

from src.graph import checkpoints


def test_checkpoint_db_path_defaults_and_join(tmp_path):
    default_path = checkpoints.checkpoint_db_path()
    assert default_path.name == "vtd_checkpoints.sqlite"
    assert default_path.parent.name == "checkpoints"

    custom = checkpoints.checkpoint_db_path(tmp_path)
    assert custom == tmp_path / "vtd_checkpoints.sqlite"


def test_build_checkpointer_returns_saver_when_dependency_available(tmp_path):
    pytest = __import__("pytest")
    pytest.importorskip("langgraph.checkpoint.sqlite")

    db_path = tmp_path / "cp.sqlite"
    checkpointer = checkpoints.build_checkpointer(db_path)

    assert checkpointer is not None
    assert Path(db_path).exists()


def test_build_checkpointer_returns_none_on_missing_dependency(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "langgraph.checkpoint.sqlite", None)

    result = checkpoints.build_checkpointer(tmp_path / "cp.sqlite")

    assert result is None
