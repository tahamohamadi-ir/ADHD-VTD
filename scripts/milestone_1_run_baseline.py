from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from _bootstrap_path import PROJECT_ROOT

CASES_PATH = PROJECT_ROOT / "data" / "questions" / "audit" / "phase0_50q_audit_cases.json"
OUT_DIR = PROJECT_ROOT / "results" / "milestone_1_baseline"


def build_prompt(question: str, schema_context: str = "") -> str:
    return f"""You are a SQLite Text-to-SQL generator.
Return strict JSON only with keys: sql, confidence, assumptions, used_tables, used_columns, result_shape, needs_clarification, clarification_question.
Only SELECT statements are allowed. Do not invent tables or columns.

SCHEMA CONTEXT:
{schema_context}

QUESTION:
{question}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="Path to GGUF model. If omitted, script runs in prompt-export mode.")
    parser.add_argument("--n", type=int, default=50)
    args = parser.parse_args()

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"][: args.n]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompts_path = OUT_DIR / "baseline_prompts.jsonl"
    results_path = OUT_DIR / "baseline_results.jsonl"

    with prompts_path.open("w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps({
                "audit_id": c["audit_id"],
                "source_id": c["source_id"],
                "question_fa": c["question_fa"],
                "prompt": build_prompt(c["question_fa"]),
            }, ensure_ascii=False) + "\n")

    if args.model is None:
        with results_path.open("w", encoding="utf-8") as f:
            for c in cases:
                f.write(json.dumps({
                    "audit_id": c["audit_id"],
                    "source_id": c["source_id"],
                    "status": "prompt_exported_only",
                    "model": None,
                    "generated_sql": None,
                    "executed_at_utc": datetime.now(timezone.utc).isoformat(),
                    "notes": "Pass --model path/to/model.gguf to run local llama-cpp generation.",
                }, ensure_ascii=False) + "\n")
        print(f"✅ Exported prompts to {prompts_path}")
        print(f"ℹ️  No model provided. Wrote placeholder results to {results_path}")
        return 0

    try:
        from llama_cpp import Llama
    except Exception as exc:
        raise RuntimeError("llama-cpp-python is required to run local baseline. Install it or run without --model.") from exc

    llm = Llama(model_path=args.model, n_ctx=4096, n_gpu_layers=-1, verbose=False)
    with results_path.open("w", encoding="utf-8") as f:
        for c in cases:
            prompt = build_prompt(c["question_fa"])
            out = llm(prompt, max_tokens=512, temperature=0.1, stop=["\n\nQUESTION:"])
            text = out["choices"][0]["text"]
            f.write(json.dumps({
                "audit_id": c["audit_id"],
                "source_id": c["source_id"],
                "status": "generated_not_validated",
                "model": args.model,
                "raw_output": text,
                "executed_at_utc": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False) + "\n")
    print(f"✅ Wrote {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
