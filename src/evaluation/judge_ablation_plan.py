from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import write_json


DEFAULT_JUDGE_MODELS = ("qwen/qwen3.6-plus", "deepseek/deepseek-v4-flash")
DEFAULT_JUDGE_POLICIES = ("semantic", "strict")


@dataclass(slots=True)
class PlannedCommand:
    label: str
    command: list[str]
    output_dir: str
    network_required: bool = False
    completion_file: str = ""


def build_dual_policy_judge_ablation_plan(
    baseline_artifact_dir: str | Path,
    adaptive_artifact_dir: str | Path,
    *,
    output_dir: str | Path,
    judge_models: list[str] | tuple[str, ...] = DEFAULT_JUDGE_MODELS,
    judge_policies: list[str] | tuple[str, ...] = DEFAULT_JUDGE_POLICIES,
    python_executable: str = r".\.venv\Scripts\python.exe",
    all_predictions: bool = True,
    judge_reasoning: bool = False,
) -> dict[str, Path]:
    root = Path(output_dir)
    baseline = Path(baseline_artifact_dir)
    adaptive = Path(adaptive_artifact_dir)
    model_list = list(judge_models)
    policy_list = list(judge_policies)
    if len(model_list) < 2:
        raise ValueError("At least two judge models are required for agreement/consensus planning.")
    if set(policy_list) != {"semantic", "strict"}:
        raise ValueError("Plan requires exactly the semantic and strict judge policies.")

    commands: list[PlannedCommand] = []
    judgment_dirs: dict[str, dict[str, dict[str, Path]]] = {"baseline": {}, "adaptive": {}}
    artifacts = {"baseline": baseline, "adaptive": adaptive}

    for variant, artifact_dir in artifacts.items():
        for policy in policy_list:
            judgment_dirs[variant].setdefault(policy, {})
            for model in model_list:
                model_slug = _slug(model)
                judge_output = root / "judgments" / f"{variant}_{policy}_{model_slug}"
                command = [
                    python_executable,
                    "scripts\\judge_benchmark_artifact.py",
                    str(artifact_dir),
                    "--output-dir",
                    str(judge_output),
                    "--judge-provider",
                    "openrouter",
                    "--judge-model",
                    model,
                    "--judge-policy",
                    policy,
                    "--all-predictions",
                    "--no-judge-reasoning" if not judge_reasoning else "--judge-reasoning",
                ]
                commands.append(
                    PlannedCommand(
                        label=f"judge_{variant}_{policy}_{model_slug}",
                        command=command,
                        output_dir=str(judge_output),
                        network_required=True,
                        completion_file="judge_summary.json",
                    )
                )
                judgment_dirs[variant][policy][model] = judge_output

    consensus_dirs: dict[str, dict[str, Path]] = {"baseline": {}, "adaptive": {}}
    for variant in artifacts:
        for policy in policy_list:
            first_two = list(judgment_dirs[variant][policy].values())[:2]
            agreement_output = root / "agreement" / f"{variant}_{policy}_{_slug(model_list[0])}_vs_{_slug(model_list[1])}"
            commands.append(
                PlannedCommand(
                    label=f"agreement_{variant}_{policy}",
                    command=[
                        python_executable,
                        "scripts\\analyze_judge_agreement.py",
                        str(first_two[0]),
                        str(first_two[1]),
                        "--output-dir",
                        str(agreement_output),
                    ],
                    output_dir=str(agreement_output),
                    completion_file="judge_agreement.json",
                )
            )

            consensus_output = root / "consensus" / f"{variant}_{policy}_consensus"
            commands.append(
                PlannedCommand(
                    label=f"consensus_{variant}_{policy}",
                    command=[
                        python_executable,
                        "scripts\\analyze_judge_consensus.py",
                        *[str(path) for path in judgment_dirs[variant][policy].values()],
                        "--output-dir",
                        str(consensus_output),
                    ],
                    output_dir=str(consensus_output),
                    completion_file="judge_consensus.json",
                )
            )
            consensus_dirs[variant][policy] = consensus_output

    dual_dirs: dict[str, Path] = {}
    for variant in artifacts:
        dual_output = root / "dual_policy" / f"{variant}_dual_policy"
        commands.append(
            PlannedCommand(
                label=f"dual_policy_{variant}",
                command=[
                    python_executable,
                    "scripts\\analyze_dual_policy_judgments.py",
                    "--semantic-dir",
                    str(consensus_dirs[variant]["semantic"]),
                    "--strict-dir",
                    str(consensus_dirs[variant]["strict"]),
                    "--output-dir",
                    str(dual_output),
                ],
                output_dir=str(dual_output),
                completion_file="dual_policy_summary.json",
            )
        )
        dual_dirs[variant] = dual_output

    ablation_output = root / "ablation" / "multi_candidate_dual_policy_ablation"
    commands.append(
        PlannedCommand(
            label="multi_candidate_dual_policy_ablation",
            command=[
                python_executable,
                "scripts\\analyze_multi_candidate_ablation.py",
                str(baseline),
                str(adaptive),
                "--baseline-dual-policy-dir",
                str(dual_dirs["baseline"]),
                "--adaptive-dual-policy-dir",
                str(dual_dirs["adaptive"]),
                "--output-dir",
                str(ablation_output),
            ],
            output_dir=str(ablation_output),
            completion_file="multi_candidate_ablation_summary.json",
        )
    )

    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "baseline_artifact_dir": str(baseline),
        "adaptive_artifact_dir": str(adaptive),
        "judge_models": model_list,
        "judge_policies": policy_list,
        "all_predictions": all_predictions,
        "judge_reasoning": judge_reasoning,
        "commands": [asdict(command) for command in commands],
        "anti_fake_policy": (
            "This plan only writes executable commands and a manifest. It does not call a judge, "
            "run a model, infer semantic labels, edit predictions, or create benchmark outcomes."
        ),
    }
    manifest_path = write_json(root / "judge_ablation_plan_manifest.json", manifest)
    ps1_path = root / "RUN_JUDGE_ABLATION.ps1"
    ps1_path.write_text(_render_powershell(commands), encoding="utf-8")
    return {"manifest": manifest_path, "powershell": ps1_path}


def _render_powershell(commands: list[PlannedCommand]) -> str:
    lines = [
        "$ErrorActionPreference = 'Stop'",
        "$env:PYTHONUNBUFFERED = '1'",
        "$env:VTD_OPENROUTER_JUDGE_RETRIES = '3'",
        "$LogPath = Join-Path $PSScriptRoot 'RUN_JUDGE_ABLATION.log'",
        "Start-Transcript -Path $LogPath -Append | Out-Null",
        "",
        "function Invoke-JudgeStep {",
        "    param(",
        "        [Parameter(Mandatory=$true)][string]$Label,",
        "        [Parameter(Mandatory=$true)][string[]]$Command,",
        "        [string]$CompletionPath = ''",
        "    )",
        "    if ($CompletionPath -and (Test-Path -LiteralPath $CompletionPath)) {",
        "        Write-Host (\"[SKIP]  {0:o} {1} completion_exists={2}\" -f (Get-Date), $Label, $CompletionPath)",
        "        return",
        "    }",
        "    $started = Get-Date",
        "    Write-Host (\"[START] {0:o} {1}\" -f $started, $Label)",
        "    Write-Host (\"[CMD] \" + ($Command -join ' '))",
        "    $CommandArgs = @()",
        "    if ($Command.Count -gt 1) {",
        "        $CommandArgs = $Command[1..($Command.Count - 1)]",
        "    }",
        "    & $Command[0] @CommandArgs",
        "    if ($LASTEXITCODE -ne 0) {",
        "        throw \"Step '$Label' failed with exit code $LASTEXITCODE\"",
        "    }",
        "    $finished = Get-Date",
        "    $elapsed = New-TimeSpan -Start $started -End $finished",
        "    Write-Host (\"[DONE]  {0:o} {1} elapsed={2}\" -f $finished, $Label, $elapsed)",
        "}",
        "",
        "try {",
    ]
    for command in commands:
        lines.append(f"    # {command.label}")
        completion_path = ""
        if command.completion_file:
            completion_path = str(Path(command.output_dir) / command.completion_file)
        lines.append(
            f"    Invoke-JudgeStep -Label {_ps_string(command.label)} "
            f"-CompletionPath {_ps_string(completion_path)} -Command @("
        )
        lines.extend(f"        {_ps_string(part)}{',' if index < len(command.command) - 1 else ''}" for index, part in enumerate(command.command))
        lines.append("    )")
        lines.append("")
    lines.append("}")
    lines.append("finally {")
    lines.append("    Stop-Transcript | Out-Null")
    lines.append("}")
    return "\n".join(lines)


def _quote_command(parts: list[str]) -> str:
    return " ".join(_ps_quote(part) for part in parts)


def _ps_quote(value: str) -> str:
    if value.startswith(".\\") or value.endswith(".exe"):
        return value
    return _ps_string(value)


def _ps_string(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _slug(value: str) -> str:
    keep: list[str] = []
    for char in value.lower():
        if char.isalnum():
            keep.append(char)
        elif char in {"-", "_"}:
            keep.append(char)
        else:
            keep.append("_")
    return "".join(keep).strip("_") or "model"
