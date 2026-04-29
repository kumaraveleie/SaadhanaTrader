"""Phase G1 — A2 shadow experiment: distance_to_stop_le_3pct → ≤4pct.

This is a **diagnostic-only** runner per the user's experiment loop.
Spec §5.4 condition #9 stays at 3% in the source (canonical contract);
this script monkey-patches the threshold to 4% at runtime so the same
replay engine can measure the delta without touching the spec or any
spec-tracked code.

Usage: ``python scripts/run_backtest_g1_shadow_stop4pct.py`` — same
arguments as ``run_backtest_g1.py`` (forwarded verbatim).

The patch happens before any condition module is imported by
``run_backtest_g1.main`` so the new threshold is visible to all
condition evaluations including the precomputed score panels.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Apply the patch BEFORE any backtest code imports the conditions module.
from saadhana_filter.indicators import conditions as _cond

_cond.DISTANCE_TO_STOP_MAX_PCT = 0.04
print(
    f"  [shadow A2] DISTANCE_TO_STOP_MAX_PCT patched: "
    f"{_cond.DISTANCE_TO_STOP_MAX_PCT} (spec value 0.03 untouched in source)",
    file=sys.stderr,
    flush=True,
)

# Make ``scripts/`` importable so we can reuse run_backtest_g1.main.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_backtest_g1 import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
