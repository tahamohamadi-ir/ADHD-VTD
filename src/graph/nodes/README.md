# `src/graph/nodes`

This package contains LangGraph node entry points and graph-local helper modules.

## Current Pattern

- `base_nodes.py` still contains the operational node implementations for compatibility with tests, monkeypatches, and existing scripts.
- Dedicated `*_node.py` modules expose the workflow-facing node imports. During incremental cleanup, they may re-export callables from `base_nodes.py`.
- Helper modules such as `candidate_orchestrator.py`, `generation_router.py`, `validation_attempts.py`, `execution_attempts.py`, `output_payloads.py`, and `reflexion_payloads.py` own small pure or dependency-injected behavior with focused tests.
- `generate_candidates_node.py` is policy-only compatibility glue. It does not call an LLM or emit SQL candidates directly.

## Rules

- Keep `workflow.py` imports pointed at the dedicated `*_node.py` modules.
- Preserve existing `base_nodes.py` wrapper names while external imports or tests depend on them.
- Do not move SQL execution out of `src/db/read_only_executor.py`.
- Do not move validation safety checks out of the validation pipeline.
- Do not put benchmark metrics, artifact promotion, gold SQL, or paper-table logic in graph node helpers.
