from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.config.paths import PROJECT_ROOT, RESULTS_DIR
from src.evaluation.ablation_flags import ablation_runtime_contract
from src.evaluation.dataset_loader import write_json


@dataclass(frozen=True, slots=True)
class AblationJob:
    config_path: Path
    config_id: str
    ablation_id: str
    command: list[str]
    declared_features: dict[str, Any]
    dataset: dict[str, Any]
    sampling: dict[str, Any]
    reporting: dict[str, Any]
    runtime_contract: dict[str, Any]
    result_status: str = "not_run"
    artifact_dir: str | None = None
    returncode: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "config_path": str(self.config_path),
            "config_id": self.config_id,
            "ablation_id": self.ablation_id,
            "command": self.command,
            "declared_features": self.declared_features,
            "dataset": self.dataset,
            "sampling": self.sampling,
            "reporting": self.reporting,
            "runtime_contract": self.runtime_contract,
            "result_status": self.result_status,
            "artifact_dir": self.artifact_dir,
            "returncode": self.returncode,
        }


def load_ablation_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Ablation config must be a YAML object: {p}")
    return data


def build_ablation_job(path: str | Path, *, python_executable: str = "python") -> AblationJob:
    p = Path(path)
    data = load_ablation_config(p)
    config_id = str(data.get("config_id") or p.stem)
    ablation_id = str(data.get("ablation_id") or config_id)
    command = [
        python_executable,
        "scripts\\run_benchmark.py",
        "--config",
        str(p),
    ]
    return AblationJob(
        config_path=p,
        config_id=config_id,
        ablation_id=ablation_id,
        command=command,
        declared_features=dict(data.get("features") or {}),
        dataset=dict(data.get("dataset") or {}),
        sampling=dict(data.get("sampling") or {}),
        reporting=dict(data.get("reporting") or {}),
        runtime_contract=ablation_runtime_contract(dict(data.get("features") or {})),
    )


def write_ablation_manifest(jobs: list[AblationJob], output_dir: str | Path | None = None) -> Path:
    if output_dir is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        root = RESULTS_DIR / "ablation" / f"{stamp}_phase11_manifest"
    else:
        root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    return write_json(
        root / "ablation_manifest.json",
        {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "result_policy": "Commands are planned runs only unless result_status is completed and artifact_dir points to a real benchmark artifact.",
            "anti_fake_policy": "not_run jobs are config manifests only; they must not be cited as benchmark metrics.",
            "jobs": [job.as_dict() for job in jobs],
        },
    )


def run_ablation_jobs(
    jobs: list[AblationJob],
    *,
    output_dir: str | Path | None = None,
    execute: bool = False,
) -> Path:
    if not execute:
        return write_ablation_manifest(jobs, output_dir)

    completed: list[AblationJob] = []
    for job in jobs:
        proc = subprocess.run(
            job.command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        artifact_dir = None
        for line in proc.stdout.splitlines():
            marker = "Benchmark artifacts written to:"
            if marker in line:
                artifact_dir = line.split(marker, 1)[1].strip()
        completed.append(
            AblationJob(
                config_path=job.config_path,
                config_id=job.config_id,
                ablation_id=job.ablation_id,
                command=job.command,
                declared_features=job.declared_features,
                dataset=job.dataset,
                sampling=job.sampling,
                reporting=job.reporting,
                runtime_contract=job.runtime_contract,
                result_status="completed" if proc.returncode == 0 and artifact_dir else "failed",
                artifact_dir=artifact_dir,
                returncode=proc.returncode,
            )
        )
    return write_ablation_manifest(completed, output_dir)
