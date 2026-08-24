from __future__ import annotations

# This script currently delegates to phase0_run_50q_manual_audit.py.
# It exists as a stable command for the Phase 0 checklist and can later aggregate
# schema freeze, value dictionary, human agreement, and stress-test reports.

from phase0_run_50q_manual_audit import main

if __name__ == "__main__":
    raise SystemExit(main())
