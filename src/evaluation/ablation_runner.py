from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.evaluation.benchmark_runner import BenchmarkRun, PredictionFn, run_benchmark
from src.evaluation.dataset_loader import write_json


@dataclass(slots=True)
class AblationConfig:
    name: str
    description: str
    paper_scope: str = "paper_1"
    enabled_features: dict[str, bool] | None = None


@dataclass(slots=True)
class AblationResult:
    config: AblationConfig
    benchmark: BenchmarkRun

    def as_dict(self) -> dict[str, Any]:
        return {
            "config": {
                "name": self.config.name,
                "description": self.config.description,
                "paper_scope": self.config.paper_scope,
                "enabled_features": self.config.enabled_features or {},
            },
            "benchmark": self.benchmark.as_dict(),
        }


DEFAULT_PAPER1_ABLATIONS = [
    AblationConfig("A0_direct_schema_only", "Direct prompt / schema-only baseline", "paper_1", {"cag": False, "reflexion": False}),
    AblationConfig("A1_plus_persian_nlu", "+ Persian normalization and routing", "paper_1", {"nlu": True}),
    AblationConfig("A2_plus_schema_linking", "+ schema linking", "paper_1", {"schema_linking": True}),
    AblationConfig("A3_plus_value_linking", "+ value linking", "paper_1", {"value_linking": True}),
    AblationConfig("A4_plus_validation", "+ safety/syntax/schema validation", "paper_1", {"validation": True}),
    AblationConfig("A5_plus_basic_repair", "+ deterministic SQL rewriter", "paper_1", {"repair": True}),
    AblationConfig("A6_plus_abstention", "+ clarification / abstention router", "paper_1", {"abstention": True}),
    AblationConfig("A7_plus_light_cag", "+ light CAG examples/skeletons", "paper_1", {"cag": True}),
]


def run_ablations(cases: list[dict[str, Any]], predictors: dict[str, PredictionFn], configs: list[AblationConfig] | None = None) -> list[AblationResult]:
    selected = configs or DEFAULT_PAPER1_ABLATIONS
    results: list[AblationResult] = []
    for cfg in selected:
        if cfg.name not in predictors:
            continue
        results.append(AblationResult(cfg, run_benchmark(cases, predictors[cfg.name], name=cfg.name)))
    return results


def write_ablation_results(results: list[AblationResult], path: str | Path) -> Path:
    return write_json(path, [r.as_dict() for r in results])
