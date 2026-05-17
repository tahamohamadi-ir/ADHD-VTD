# `experiments/configs`

This folder stores experiment and ablation configs.

Important rule: a config is not a result. Paper tables can only use metrics from real benchmark artifacts under `results/benchmark/`.

## Phase 11 First-Paper Templates

| File | Purpose | Result status |
|---|---|---|
| `A0_direct_schema_only.yaml` | Minimal direct baseline with CAG disabled | config only |
| `A1_persian_nlu.yaml` | Adds Persian normalization/routing | config only |
| `A2_schema_linking.yaml` | Schema-linking template | config only |
| `A3_value_linking.yaml` | Value-linking template | config only |
| `A4_cag_examples.yaml` | Adds CAG examples with `exclude_self=true` | config only |
| `A7_full_phase10_system.yaml` | Current full Phase-10 infrastructure | config only; has closest smoke artifact noted |

Run each config explicitly:

```powershell
python scripts\run_benchmark.py --config experiments\configs\A7_full_phase10_system.yaml
```

After each run, analyze the generated artifact:

```powershell
python scripts\analyze_benchmark_artifact.py results\benchmark\<artifact-folder>
```

## Anti-Overfit Rules

- Keep `exclude_self: true` for dev/test.
- Do not modify prompts or validators for a single case ID before running the ablation matrix.
- Do not compare configs unless the evaluated case IDs match or the report clearly says the comparison is descriptive only.
- Keep model path, dataset hash, selected-case hash and module flags in every report.

## Existing Legacy Experiment Configs

The `exp_*.yaml` files are earlier experiment sketches. They can be kept for history, but Phase 11 paper claims should use the `A*.yaml` configs or a documented successor matrix.
