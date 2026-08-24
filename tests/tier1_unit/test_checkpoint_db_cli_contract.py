from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from scripts.run_benchmark import build_parser


def test_run_benchmark_parser_accepts_checkpoint_db_flag():
    args = build_parser().parse_args(
        [
            "--mode",
            "agent",
            "--dataset",
            "dev",
            "--samples-per-level",
            "1",
            "--checkpoint-db",
            "logs/checkpoints/vtd_checkpoints.sqlite",
        ]
    )

    assert args.checkpoint_db == "logs/checkpoints/vtd_checkpoints.sqlite"


def test_run_benchmark_parser_checkpoint_db_defaults_to_none():
    args = build_parser().parse_args(["--mode", "agent", "--dataset", "dev"])

    assert args.checkpoint_db is None
