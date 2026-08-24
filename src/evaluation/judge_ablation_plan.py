from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from src.evaluation.dataset_loader import read_json, write_json

DEFAULT_JUDGE_MODELS = ("qwen/qwen3.6-plus", "deepseek/deepseek-v4-flash")
DEFAULT_JUDGE_POLICIES = ("semantic", "strict")


@dataclass(slots=True)
class PlannedCommand:
    label: str
    command: list[str]
    output_dir: str
    network_required: bool = False
    completion_file: str = ""


@dataclass(frozen=True, slots=True)
class JudgeAblationPlanIssue:
    code: str
    message: str
    path: str | None = None
    severity: str = "error"

    def as_dict(self) -> dict[str, str]:
        payload = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.path is not None:
            payload["path"] = self.path
        return payload


@dataclass(frozen=True, slots=True)
class JudgeAblationPlanValidationReport:
    ok: bool
    issues: list[JudgeAblationPlanIssue] = field(default_factory=list)
    checked: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [issue.as_dict() for issue in self.issues],
            "checked": self.checked,
        }


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
    judgment_dirs: dict[str, dict[str, dict[str, Path]]] = {
        "baseline": {},
        "adaptive": {},
    }
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
                    "--no-judge-reasoning" if not judge_reasoning else "--judge-reasoning",
                ]
                if all_predictions:
                    command.insert(-1, "--all-predictions")
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
            agreement_output = (
                root
                / "agreement"
                / f"{variant}_{policy}_{_slug(model_list[0])}_vs_{_slug(model_list[1])}"
            )
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


def validate_dual_policy_judge_ablation_plan(
    plan_dir: str | Path,
) -> JudgeAblationPlanValidationReport:
    root = Path(plan_dir)
    manifest_path = (
        root
        if root.name == "judge_ablation_plan_manifest.json"
        else root / "judge_ablation_plan_manifest.json"
    )
    plan_root = manifest_path.parent
    runbook_path = plan_root / "RUN_JUDGE_ABLATION.ps1"
    issues: list[JudgeAblationPlanIssue] = []
    checked: dict[str, Any] = {
        "manifest": str(manifest_path),
        "powershell": str(runbook_path),
    }

    if not manifest_path.exists():
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_MANIFEST_MISSING",
                message=f"Judge ablation plan manifest is missing: {manifest_path}",
                path=str(manifest_path),
            )
        )
        return JudgeAblationPlanValidationReport(ok=False, issues=issues, checked=checked)

    try:
        manifest = read_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_MANIFEST_INVALID_JSON",
                message=f"Could not read judge ablation plan manifest: {exc}",
                path=str(manifest_path),
            )
        )
        return JudgeAblationPlanValidationReport(ok=False, issues=issues, checked=checked)

    if not isinstance(manifest, dict):
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_MANIFEST_NOT_OBJECT",
                message="Judge ablation plan manifest must be a JSON object.",
                path=str(manifest_path),
            )
        )
        return JudgeAblationPlanValidationReport(ok=False, issues=issues, checked=checked)

    _validate_plan_header(manifest, issues, manifest_path, checked)
    commands = manifest.get("commands")
    if isinstance(commands, list):
        _validate_plan_commands(manifest, commands, issues, manifest_path, checked)
    else:
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_COMMANDS_MISSING",
                message="Judge ablation plan manifest must contain a commands list.",
                path=str(manifest_path),
            )
        )

    if not runbook_path.exists():
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_RUNBOOK_MISSING",
                message=f"Judge ablation PowerShell runbook is missing: {runbook_path}",
                path=str(runbook_path),
            )
        )
    else:
        runbook = runbook_path.read_text(encoding="utf-8")
        checked["powershell_has_transcript"] = "Start-Transcript" in runbook
        checked["powershell_has_step_wrapper"] = "Invoke-JudgeStep" in runbook
        if "Start-Transcript" not in runbook or "Invoke-JudgeStep" not in runbook:
            issues.append(
                JudgeAblationPlanIssue(
                    code="PLAN_RUNBOOK_UNSAFE_SHAPE",
                    message="Judge ablation runbook must log and run through Invoke-JudgeStep.",
                    path=str(runbook_path),
                )
            )

    return JudgeAblationPlanValidationReport(
        ok=not issues,
        issues=issues,
        checked=checked,
    )


def _validate_plan_header(
    manifest: dict[str, Any],
    issues: list[JudgeAblationPlanIssue],
    manifest_path: Path,
    checked: dict[str, Any],
) -> None:
    baseline_value = manifest.get("baseline_artifact_dir")
    adaptive_value = manifest.get("adaptive_artifact_dir")
    baseline = Path(str(baseline_value)) if baseline_value else None
    adaptive = Path(str(adaptive_value)) if adaptive_value else None
    checked["baseline_artifact_dir"] = str(baseline) if baseline else ""
    checked["adaptive_artifact_dir"] = str(adaptive) if adaptive else ""
    checked["baseline_artifact_exists"] = bool(baseline and baseline.exists())
    checked["adaptive_artifact_exists"] = bool(adaptive and adaptive.exists())
    if baseline is None or not baseline.exists():
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_BASELINE_ARTIFACT_MISSING",
                message=f"Baseline benchmark artifact path is missing: {baseline_value}",
                path=str(manifest_path),
            )
        )
    if adaptive is None or not adaptive.exists():
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_ADAPTIVE_ARTIFACT_MISSING",
                message=f"Adaptive benchmark artifact path is missing: {adaptive_value}",
                path=str(manifest_path),
            )
        )

    models = manifest.get("judge_models")
    policies = manifest.get("judge_policies")
    checked["judge_model_count"] = len(models) if isinstance(models, list) else 0
    checked["judge_policies"] = policies if isinstance(policies, list) else []
    if not isinstance(models, list) or len(models) < 2 or len(set(models)) != len(models):
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_JUDGE_MODELS_INVALID",
                message="Judge ablation plan requires at least two unique judge models.",
                path=str(manifest_path),
            )
        )
    if set(policies or []) != {"semantic", "strict"}:
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_JUDGE_POLICIES_INVALID",
                message="Judge ablation plan must include exactly semantic and strict policies.",
                path=str(manifest_path),
            )
        )
    if not isinstance(manifest.get("all_predictions"), bool):
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_ALL_PREDICTIONS_NOT_BOOL",
                message="Judge ablation plan must record all_predictions as a boolean.",
                path=str(manifest_path),
            )
        )

    anti_fake_policy = str(manifest.get("anti_fake_policy") or "").lower()
    checked["anti_fake_policy_present"] = bool(anti_fake_policy)
    required_fragments = [
        "does not call a judge",
        "infer semantic labels",
        "create benchmark outcomes",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in anti_fake_policy]
    if missing:
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_ANTI_FAKE_POLICY_INCOMPLETE",
                message="Judge ablation plan must explicitly state that it is not result evidence.",
                path=str(manifest_path),
            )
        )


def _validate_plan_commands(
    manifest: dict[str, Any],
    commands: list[Any],
    issues: list[JudgeAblationPlanIssue],
    manifest_path: Path,
    checked: dict[str, Any],
) -> None:
    models = manifest.get("judge_models") if isinstance(manifest.get("judge_models"), list) else []
    expected_total = 4 * len(models) + 11 if models else None
    labels: list[str] = []
    judge_policy_counts = {"semantic": 0, "strict": 0}
    network_required_count = 0
    all_predictions = bool(manifest.get("all_predictions"))

    for raw_command in commands:
        if not isinstance(raw_command, dict):
            issues.append(
                JudgeAblationPlanIssue(
                    code="PLAN_COMMAND_NOT_OBJECT",
                    message="Each judge ablation command must be an object.",
                    path=str(manifest_path),
                )
            )
            continue
        label = str(raw_command.get("label") or "")
        command = raw_command.get("command")
        completion_file = str(raw_command.get("completion_file") or "")
        output_dir = str(raw_command.get("output_dir") or "")
        labels.append(label)
        if raw_command.get("network_required") is True:
            network_required_count += 1
        if not label or not isinstance(command, list) or not output_dir or not completion_file:
            issues.append(
                JudgeAblationPlanIssue(
                    code="PLAN_COMMAND_INCOMPLETE",
                    message="Every plan command needs label, command list, output_dir, and completion_file.",
                    path=str(manifest_path),
                )
            )
            continue
        command_parts = [str(part) for part in command]
        _validate_single_plan_command(
            label,
            command_parts,
            completion_file,
            bool(raw_command.get("network_required")),
            all_predictions,
            judge_policy_counts,
            issues,
            manifest_path,
        )

    checked["command_count"] = len(commands)
    checked["network_required_commands"] = network_required_count
    checked["judge_policy_counts"] = judge_policy_counts
    if expected_total is not None and len(commands) != expected_total:
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_COMMAND_COUNT_INVALID",
                message=f"Expected {expected_total} commands for {len(models)} models, found {len(commands)}.",
                path=str(manifest_path),
            )
        )
    if len(set(labels)) != len(labels):
        issues.append(
            JudgeAblationPlanIssue(
                code="PLAN_COMMAND_LABEL_DUPLICATE",
                message="Judge ablation plan command labels must be unique.",
                path=str(manifest_path),
            )
        )
    for policy, count in judge_policy_counts.items():
        expected_policy_count = 2 * len(models)
        if models and count != expected_policy_count:
            issues.append(
                JudgeAblationPlanIssue(
                    code="PLAN_JUDGE_POLICY_COMMAND_COUNT_INVALID",
                    message=(
                        f"Expected {expected_policy_count} judge commands for {policy}, found {count}."
                    ),
                    path=str(manifest_path),
                )
            )


def _validate_single_plan_command(
    label: str,
    command: list[str],
    completion_file: str,
    network_required: bool,
    all_predictions: bool,
    judge_policy_counts: dict[str, int],
    issues: list[JudgeAblationPlanIssue],
    manifest_path: Path,
) -> None:
    if label.startswith("judge_"):
        policy = _command_option_value(command, "--judge-policy")
        if policy in judge_policy_counts:
            judge_policy_counts[policy] += 1
        if "scripts\\judge_benchmark_artifact.py" not in command:
            _append_command_issue(
                issues, manifest_path, label, "must call judge_benchmark_artifact.py"
            )
        if _command_option_value(command, "--judge-provider") != "openrouter":
            _append_command_issue(
                issues, manifest_path, label, "must use the openrouter judge provider"
            )
        if _command_option_value(command, "--judge-model") is None:
            _append_command_issue(issues, manifest_path, label, "must record a judge model")
        if policy not in {"semantic", "strict"}:
            _append_command_issue(
                issues, manifest_path, label, "must use semantic or strict policy"
            )
        if completion_file != "judge_summary.json":
            _append_command_issue(
                issues, manifest_path, label, "must complete with judge_summary.json"
            )
        if not network_required:
            _append_command_issue(
                issues, manifest_path, label, "must be marked network_required=true"
            )
        has_all_predictions = "--all-predictions" in command
        if all_predictions and not has_all_predictions:
            _append_command_issue(issues, manifest_path, label, "must include --all-predictions")
        if not all_predictions and has_all_predictions:
            _append_command_issue(
                issues, manifest_path, label, "must not include --all-predictions"
            )
        return

    if network_required:
        _append_command_issue(
            issues, manifest_path, label, "offline analysis must not require network"
        )
    if label.startswith("agreement_"):
        expected = ("scripts\\analyze_judge_agreement.py", "judge_agreement.json")
    elif label.startswith("consensus_"):
        expected = ("scripts\\analyze_judge_consensus.py", "judge_consensus.json")
    elif label.startswith("dual_policy_"):
        expected = (
            "scripts\\analyze_dual_policy_judgments.py",
            "dual_policy_summary.json",
        )
        if "--semantic-dir" not in command or "--strict-dir" not in command:
            _append_command_issue(
                issues,
                manifest_path,
                label,
                "must keep semantic and strict dirs explicit",
            )
    elif label == "multi_candidate_dual_policy_ablation":
        expected = (
            "scripts\\analyze_multi_candidate_ablation.py",
            "multi_candidate_ablation_summary.json",
        )
        if (
            "--baseline-dual-policy-dir" not in command
            or "--adaptive-dual-policy-dir" not in command
        ):
            _append_command_issue(
                issues, manifest_path, label, "must keep dual-policy inputs explicit"
            )
    else:
        _append_command_issue(issues, manifest_path, label, "has an unknown command role")
        return
    expected_script, expected_completion = expected
    if expected_script not in command:
        _append_command_issue(issues, manifest_path, label, f"must call {expected_script}")
    if completion_file != expected_completion:
        _append_command_issue(
            issues, manifest_path, label, f"must complete with {expected_completion}"
        )


def _command_option_value(command: list[str], option: str) -> str | None:
    try:
        index = command.index(option)
    except ValueError:
        return None
    if index + 1 >= len(command):
        return None
    return command[index + 1]


def _append_command_issue(
    issues: list[JudgeAblationPlanIssue],
    manifest_path: Path,
    label: str,
    message: str,
) -> None:
    issues.append(
        JudgeAblationPlanIssue(
            code="PLAN_COMMAND_INVALID",
            message=f"Command {label!r} {message}.",
            path=str(manifest_path),
        )
    )


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
        '        Write-Host ("[SKIP]  {0:o} {1} completion_exists={2}" -f (Get-Date), $Label, $CompletionPath)',
        "        return",
        "    }",
        "    $started = Get-Date",
        '    Write-Host ("[START] {0:o} {1}" -f $started, $Label)',
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
        '    Write-Host ("[DONE]  {0:o} {1} elapsed={2}" -f $finished, $Label, $elapsed)',
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
        lines.extend(
            f"        {_ps_string(part)}{',' if index < len(command.command) - 1 else ''}"
            for index, part in enumerate(command.command)
        )
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
