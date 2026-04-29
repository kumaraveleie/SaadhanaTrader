"""Shared enums and dataclasses for the signal engine.

Public-mode label translation (BUY → "High Pattern Match", etc.) lives
in the Next.js layer per §21 — Python code uses the internal labels
unmodified.
"""

from __future__ import annotations

from enum import StrEnum


class SignalState(StrEnum):
    """§3 — the four canonical signal states (plus WATCH per §5).

    WATCH is a display-only status (score 10–12) that surfaces in the
    scanner but never triggers a trade per §3.
    """

    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    WAIT = "WAIT"
    WATCH = "WATCH"
