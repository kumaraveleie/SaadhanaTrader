"""Path γ — Information-budget diagnostic per Sec.0.7.5 class.

Estimates the "remaining information budget per class after universe
filter" on InvestQuest. The Phase 1 finding (Tier 2 v0 produces 0pp
lift because 99.8% of universe symbols pass) suggested the universe
filter is itself an implicit class-2 quality filter. This script
checks whether the same saturation hits classes 3 (catalysts), 4
(institutional flow), and 6 (regime) — before we commit to the
4-week Phase 2 build.

Method per class: pick a sample of (symbol, date) pairs; compute the
class signal at each pair; count what fraction "passes" the class's
typical gate. If pass-rate is near 100% or near 0%, the class is
saturated on this universe and adding it as a Diamond layer won't
discriminate. Sweet-spot pass-rate is roughly 30–70% (room to
discriminate winners from losers).
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "filter"))

from saadhana_filter.catalysts.daily import build_all_catalysts  # noqa: E402
from saadhana_filter.data.loader import load_eod  # noqa: E402
from saadhana_filter.data.universe import load_universe  # noqa: E402
from saadhana_filter.indicators.primitives import macd, rsi  # noqa: E402
from saadhana_filter.signals.regime import market_regime  # noqa: E402

N_SAMPLES = 100
RNG_SEED = 20260503


def _build_nifty_proxy() -> pd.Series:
    """Universe-mean close as Nifty proxy (no Nifty index in cache)."""
    from datetime import date as _date, timedelta as _td
    universe = load_universe()
    if len(universe) == 0:
        universe = load_universe(as_of_date=_date.today() - _td(days=1))
    closes = []
    for sym in list(universe.head(50).index):
        try:
            df = load_eod(sym)
        except Exception:
            continue
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        if "close" not in df.columns or len(df) < 100:
            continue
        norm = df["close"] / df["close"].iloc[0] * 100.0
        closes.append(norm.rename(sym))
    if not closes:
        return pd.Series(dtype=float)
    return pd.concat(closes, axis=1).mean(axis=1)


def _sample_pairs(universe: pd.DataFrame, n: int = N_SAMPLES) -> list[tuple[str, pd.Timestamp]]:
    """Random (symbol, date) pairs from the universe over 2023-04-03
    → 2026-05-02. The sample mixes random universe symbols with random
    dates to estimate the class-signal pass-rate without conditioning
    on the cohort firing."""
    rng = np.random.default_rng(RNG_SEED)
    syms = list(universe.index)
    pool_dates = pd.date_range("2023-06-01", "2026-04-15", freq="B")  # business days
    pairs: list[tuple[str, pd.Timestamp]] = []
    for _ in range(n * 4):
        if len(pairs) >= n:
            break
        sym = syms[int(rng.integers(0, len(syms)))]
        d = pool_dates[int(rng.integers(0, len(pool_dates)))]
        try:
            df = load_eod(sym)
        except Exception:
            continue
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        if df.index.searchsorted(d) >= len(df) or df.index[df.index.searchsorted(d)] != d:
            continue
        pairs.append((sym, d))
    return pairs


# ─────────────────────────────────────────────────────────────────────
# Class 1 — price-pattern technicals (3-way agreement among RSI / MACD / fast-vs-slow MA)
# ─────────────────────────────────────────────────────────────────────
def _class1_signals(pairs: list[tuple[str, pd.Timestamp]]) -> dict:
    """For each pair, compute 3 trend signals: RSI > 50, MACD line >
    signal, EMA20 > EMA50. Cross-tab agreement."""
    from saadhana_filter.indicators.primitives import ema
    rsi_pos = 0
    macd_pos = 0
    ema_pos = 0
    all_three = 0
    n_eval = 0
    for sym, d in pairs:
        try:
            df = load_eod(sym)
        except Exception:
            continue
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        bar = int(df.index.searchsorted(d))
        if bar >= len(df) or bar < 50:
            continue
        rsi14 = rsi(df["close"], 14)
        macd_df = macd(df["close"], 12, 26, 9)
        ema20 = ema(df["close"], 20)
        ema50 = ema(df["close"], 50)
        r = rsi14.iloc[bar]
        m = macd_df["macd"].iloc[bar]
        ms = macd_df["signal"].iloc[bar]
        e20 = ema20.iloc[bar]
        e50 = ema50.iloc[bar]
        if any(pd.isna(v) for v in (r, m, ms, e20, e50)):
            continue
        a = bool(r > 50)
        b = bool(m > ms)
        c = bool(e20 > e50)
        rsi_pos += int(a)
        macd_pos += int(b)
        ema_pos += int(c)
        all_three += int(a and b and c)
        n_eval += 1
    return {
        "n": n_eval,
        "rsi_pass_pct": 100.0 * rsi_pos / n_eval if n_eval else 0.0,
        "macd_pass_pct": 100.0 * macd_pos / n_eval if n_eval else 0.0,
        "ema_stack_pass_pct": 100.0 * ema_pos / n_eval if n_eval else 0.0,
        "all_three_agree_pct": 100.0 * all_three / n_eval if n_eval else 0.0,
    }


# ─────────────────────────────────────────────────────────────────────
# Class 3 — catalyst pass-rate
# ─────────────────────────────────────────────────────────────────────
def _class3_signals(pairs: list[tuple[str, pd.Timestamp]]) -> dict:
    """For each pair, query the catalyst engine for that date.
    Count: (a) at least 1 active catalyst, (b) ≥ 2 active catalysts.

    The Phase D catalyst engine is fixture-based today — its coverage
    of historical (symbol, date) pairs is sparse. The diagnostic just
    measures what we can observe with the existing infrastructure;
    Phase 2A live scrapers would replace fixtures with real data.
    """
    by_date: dict[pd.Timestamp, list[str]] = {}
    for sym, d in pairs:
        by_date.setdefault(d, []).append(sym)

    n_with_any = 0
    n_with_2plus = 0
    n_eval = 0
    fii_increase_count = 0
    dii_increase_count = 0
    for d, syms in by_date.items():
        try:
            day_summaries = build_all_catalysts(today=d.date())
        except Exception:
            continue
        for sym in syms:
            n_eval += 1
            summary = day_summaries.get(sym)
            if summary is None:
                continue
            n_active = summary.catalyst_count_fresh + summary.catalyst_count_recent
            if n_active >= 1:
                n_with_any += 1
            if n_active >= 2:
                n_with_2plus += 1
            for cat in summary.catalysts:
                t = getattr(cat, "type", None)
                if t == "fii_increase":
                    fii_increase_count += 1
                if t == "dii_increase":
                    dii_increase_count += 1
    return {
        "n": n_eval,
        "any_catalyst_pct": 100.0 * n_with_any / n_eval if n_eval else 0.0,
        "two_plus_pct": 100.0 * n_with_2plus / n_eval if n_eval else 0.0,
        "fii_increase_count": fii_increase_count,
        "dii_increase_count": dii_increase_count,
    }


# ─────────────────────────────────────────────────────────────────────
# Class 6 — market regime distribution
# ─────────────────────────────────────────────────────────────────────
def _class6_regime() -> dict:
    """Compute the market_regime time-series over the test window and
    aggregate by regime label."""
    nifty_close = _build_nifty_proxy()
    if nifty_close.empty:
        return {"err": "no Nifty proxy data"}
    # market_regime expects a DataFrame with at least a close column;
    # build a minimal frame.
    df = pd.DataFrame({"close": nifty_close})
    try:
        regime = market_regime(df)
    except Exception as exc:
        return {"err": f"regime calculation failed: {exc}"}
    cnt = regime.value_counts(dropna=True).sort_index()
    total = int(cnt.sum())
    return {
        "n_bars": total,
        "by_regime": {
            str(k): {"n": int(v), "pct": 100.0 * v / total} for k, v in cnt.items()
        },
    }


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
def _budget_label(pass_pct: float) -> str:
    """Map a pass-rate to a remaining-budget classification."""
    # Sweet spot: 30-70% pass rate has discrimination room.
    # Saturated: > 85% or < 15% has near-zero remaining budget.
    if pass_pct >= 95.0:
        return "ZERO (saturated, ~all pass — no discrimination)"
    if pass_pct >= 85.0:
        return "LOW (most symbols pass)"
    if pass_pct >= 30.0 and pass_pct <= 70.0:
        return "HIGH (sweet-spot — discrimination possible)"
    if pass_pct >= 15.0 and pass_pct < 30.0:
        return "MEDIUM (skewed toward fails — fewer winners)"
    return "LOW (skewed toward fails — most reject)"


def main() -> int:
    print("Path γ — orthogonality-budget diagnostic")
    print(f"Sample size: {N_SAMPLES} (symbol, date) pairs over 2023-06 → 2026-04")
    print(f"Seed: {RNG_SEED}")

    universe = load_universe()
    if len(universe) == 0:
        universe = load_universe(as_of_date=date.today() - timedelta(days=1))
    print(f"Universe: {len(universe)} symbols")

    print("\nSampling random (symbol, date) pairs...")
    pairs = _sample_pairs(universe, n=N_SAMPLES)
    print(f"  Drew {len(pairs)} valid pairs")

    print("\nClass 1 — price-pattern technicals (RSI / MACD / EMA stack)...")
    c1 = _class1_signals(pairs)
    print(f"  N evaluated: {c1['n']}")
    print(f"  RSI > 50:               {c1['rsi_pass_pct']:>5.1f}%")
    print(f"  MACD line > signal:     {c1['macd_pass_pct']:>5.1f}%")
    print(f"  EMA20 > EMA50:          {c1['ema_stack_pass_pct']:>5.1f}%")
    print(f"  ALL THREE agree:        {c1['all_three_agree_pct']:>5.1f}%")

    print("\nClass 2 — company quality (Phase 1 result, no re-test)")
    print("  Tier 2 v0 score = 5 / 5: 99.8%")

    print("\nClass 3 — catalysts (Phase D fixture engine)...")
    c3 = _class3_signals(pairs)
    print(f"  N evaluated: {c3['n']}")
    print(f"  Any active catalyst:    {c3['any_catalyst_pct']:>5.1f}%")
    print(f"  ≥ 2 active catalysts:   {c3['two_plus_pct']:>5.1f}%")
    print(f"  fii_increase tag count: {c3['fii_increase_count']}")
    print(f"  dii_increase tag count: {c3['dii_increase_count']}")

    print("\nClass 4 — institutional flow (FII/DII tag count from class 3)")
    fii_pct = (
        100.0 * c3["fii_increase_count"] / c3["n"] if c3["n"] else 0.0
    )
    dii_pct = (
        100.0 * c3["dii_increase_count"] / c3["n"] if c3["n"] else 0.0
    )
    print(f"  fii_increase tag rate:  {fii_pct:>5.1f}% of pairs")
    print(f"  dii_increase tag rate:  {dii_pct:>5.1f}% of pairs")

    print("\nClass 5 — sector breadth (Phase 1 / Track 3 known empirical)")
    print("  Layer 6 lift on TC 3-of-3: +7.2pp hit rate — HIGH remaining budget")

    print("\nClass 6 — market regime distribution (3-year proxy)")
    c6 = _class6_regime()
    if "err" in c6:
        print(f"  WARN: {c6['err']}")
    else:
        print(f"  N bars: {c6['n_bars']}")
        for r, d in c6["by_regime"].items():
            print(f"    {r:<20} {d['n']:>5} bars ({d['pct']:>5.1f}%)")

    # ─── Summary table ───
    print()
    print("=" * 110)
    print("ORTHOGONALITY-BUDGET SUMMARY")
    print("=" * 110)
    print(
        f"| {'Class':<7} | {'Description':<35} | {'Pass-rate observed':<25} | "
        f"{'Remaining budget':<35} |"
    )
    print(f"|{'-' * 9}|{'-' * 37}|{'-' * 27}|{'-' * 37}|")

    rows = []
    rows.append({
        "class": "1",
        "desc": "Price-pattern technicals",
        "rate": f"{c1['all_three_agree_pct']:.1f}%",
        "label": _budget_label(c1["all_three_agree_pct"]),
        "build": "Already built (TC, Pro-setup, etc.)",
    })
    rows.append({
        "class": "2",
        "desc": "Company quality (v0)",
        "rate": "99.8%",
        "label": "ZERO (Phase 1 confirmed)",
        "build": "NO — saturated by universe filter",
    })
    rows.append({
        "class": "3",
        "desc": "Catalysts (≥ 2 active)",
        "rate": f"{c3['two_plus_pct']:.1f}%",
        "label": _budget_label(c3["two_plus_pct"]),
        "build": "?",
    })
    rows.append({
        "class": "4",
        "desc": "FII flow (FII_INCREASE tag)",
        "rate": f"{fii_pct:.1f}%",
        "label": _budget_label(fii_pct),
        "build": "?",
    })
    rows.append({
        "class": "5",
        "desc": "Sector breadth",
        "rate": "(empirical)",
        "label": "HIGH (+7.2pp lift on Layer 6)",
        "build": "Already built (Layer 6)",
    })
    if "err" not in c6:
        regime_pcts = [d["pct"] for d in c6["by_regime"].values()]
        c6_label = (
            "HIGH (regime distribution is well-spread)"
            if max(regime_pcts) <= 85
            else "MEDIUM (one regime dominates)"
        )
    else:
        c6_label = f"UNKNOWN ({c6['err']})"
    rows.append({
        "class": "6",
        "desc": "Market regime",
        "rate": (
            "spread "
            f"{[round(d['pct'], 1) for d in c6['by_regime'].values()] if 'err' not in c6 else 'n/a'}"
        ),
        "label": c6_label,
        "build": "Build alongside Adaptive Suite",
    })

    for r in rows:
        print(
            f"| {r['class']:<7} | {r['desc']:<35} | {r['rate']:<25} | {r['label']:<35} |"
        )

    # ─── Phase 2 recommendation ───
    print()
    print("=" * 110)
    print("PATH γ CHECKPOINT — Phase 2 (catalyst layer) recommendation")
    print("=" * 110)
    c3_label = _budget_label(c3["two_plus_pct"])
    if c3["any_catalyst_pct"] < 1.0:
        verdict = (
            "STOP — fixture-based catalyst engine returns ZERO catalysts on the "
            "diagnostic sample. The infrastructure cannot produce historical "
            "evidence for or against Phase 2's hypothesis. Phase 2A scrapers "
            "(live data) MUST land before any catalyst-layer backtest is "
            "possible. Without them, Path γ cannot greenlight Phase 2."
        )
    elif "HIGH" in c3_label:
        verdict = (
            f"PROCEED with Phase 2 — class 3 catalysts are observed at "
            f"{c3['two_plus_pct']:.1f}% (≥ 2 active) which sits in the "
            f"discriminating sweet-spot. Expected lift on TC hit rate: 5–10pp."
        )
    elif "MEDIUM" in c3_label:
        verdict = (
            f"MIXED — class 3 catalysts observed at {c3['two_plus_pct']:.1f}%. "
            "Phase 2 likely contributes some lift but possibly less than the "
            "Diamond budget assumed. Operator decision."
        )
    else:
        verdict = (
            f"SKIP Phase 2 — class 3 catalysts observed at "
            f"{c3['two_plus_pct']:.1f}% on diagnostic sample. Likely saturated."
        )
    print()
    print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
