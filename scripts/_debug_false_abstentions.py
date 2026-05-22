"""Debug script: inspect false-abstention and safety-false-positive cases from artifact."""
import json
import pathlib
import sys

art = pathlib.Path(
    "results/benchmark/"
    "20260516_073203_agent_dev_qwen2_5-coder-3b-instruct-q4_k_m_full_trace_balanced_dev"
)

# List all files in artifact directory
print("Files in artifact dir:")
for f in sorted(art.iterdir()):
    print(f"  {f.name}  ({f.stat().st_size} bytes)")
print()

# Try predictions first, then partial, then failures
preds_files = sorted(art.glob("*_predictions.jsonl"))
partial_files = sorted(art.glob("*_partial_predictions.jsonl"))
failure_files = sorted(art.glob("*_failures.jsonl"))

# Prefer non-partial predictions; fall back to partial
chosen_preds = [f for f in preds_files if "_partial_" not in f.name]
if not chosen_preds:
    chosen_preds = partial_files

chosen_fail = failure_files[0] if failure_files else None

print(f"Using predictions file: {chosen_preds[0].name if chosen_preds else 'NONE'}")
print(f"Using failures file   : {chosen_fail.name if chosen_fail else 'NONE'}")
print()

# Load all predictions rows and show all case IDs
all_preds = {}
if chosen_preds:
    for line in chosen_preds[0].read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        p = json.loads(line)
        cid = p.get("case_id", p.get("id", "?"))
        all_preds[cid] = p

print(f"Total prediction rows found: {len(all_preds)}")
print("Case IDs in predictions file:")
for cid in sorted(all_preds.keys()):
    p = all_preds[cid]
    print(f"  {cid} | action={p.get('actual_action','?')} | error={p.get('error_type','?')} | diff={p.get('difficulty','?')}")
print()

# Load failures
all_fails = {}
if chosen_fail:
    for line in chosen_fail.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        f = json.loads(line)
        cid = f.get("case_id", f.get("id", "?"))
        all_fails[cid] = f

out_file = pathlib.Path("results/error_analysis/20260522_balanced_dev_3b_deep_analysis/debug_output.txt")
with open(out_file, "w", encoding="utf-8") as out:
    out.write(f"Total failure rows found: {len(all_fails)}\n")
    out.write("Failures details:\n")
    out.write("-" * 70 + "\n")
    for cid in sorted(all_fails.keys()):
        f = all_fails[cid]
        q = f.get("question", f.get("normalized_question", ""))
        out.write(f"--- {cid} | diff={f.get('difficulty','?')} | error={f.get('error_type','?')} ---\n")
        out.write(f"  question    : {q[:160]}\n")
        out.write(f"  intent      : {f.get('intent','?')}\n")
        out.write(f"  is_unsafe   : {f.get('is_unsafe','?')}\n")
        out.write(f"  is_ambiguous: {f.get('is_ambiguous','?')}\n")
        out.write(f"  actual_action: {f.get('actual_action','?')}\n")
        out.write(f"  valid_sql   : {f.get('valid_sql','?')}\n")
        val = f.get("validation_issues", [])
        if val:
            out.write(f"  val_issues  : {val[:3]}\n")
        out.write("\n")

print(f"Output written to {out_file}")
