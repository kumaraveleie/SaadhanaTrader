"""Phase G1 A4 — trade-level audit of A1's STOP_HIT trades.

Reads the A1 trade list (industrial-only, 3pct stop), recomputes the
per-trade features the user requested in the A4 brief, and emits a
markdown report at ``spec/samples/backtest_g1_a4_stopout_audit.md``.

Per-trade features captured:
  - days_to_stop                  (entry → exit calendar days)
  - regime_at_entry / _at_exit    (Risk_On / Caution / Risk_Off + shifted?)
  - rvol_at_entry                 (volume / 50-bar prior mean)
  - atr_pct_of_close_at_entry     (ATR(14) as % of close)
  - atr_percentile_252b           (entry-day ATR vs trailing 252-bar)
  - days_since_52wh_at_entry      (calendar days since high == 52WH)
  - max_favorable_excursion_pct   (best close after entry)
  - max_adverse_excursion_pct     (worst close after entry)
  - biggest_down_day_pct          (largest single-bar fall in the trade)
  - sub_industry                  (NSE Industry from the constituent CSV)

Then a "Cluster patterns" section flagging features where ≥ 25 of 41
trades share a property (the user-defined density threshold).
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from saadhana_filter.data.loader import load_eod
from saadhana_filter.indicators.primitives import atr, rvol
from saadhana_filter.signals.regime import market_regime

# ──────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
TRADES_PATH = ROOT / "spec" / "samples" / "backtest_g1_nifty500_excl_fin_trades.json"
CONSTITUENTS_PATH = ROOT / "data" / "nifty500_constituents.csv"
REPORT_PATH = ROOT / "spec" / "samples" / "backtest_g1_a4_stopout_audit.md"

CLUSTER_DENSITY_THRESHOLD = 25  # ≥ 25 of 41 trades share the feature
CLUSTER_DENSITY_DENOMINATOR_HINT = 41


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────
def _load_industries() -> dict[str, str]:
    """Map NSE symbol → Industry from the bundled Nifty 500 CSV."""
    out: dict[str, str] = {}
    if not CONSTITUENTS_PATH.exists():
        return out
    with open(CONSTITUENTS_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sym = row.get("Symbol", "").strip()
            ind = row.get("Industry", "").strip()
            if sym and ind:
                out[sym] = ind
    return out


def _load_index() -> pd.DataFrame:
    import yfinance as yf

    df = yf.Ticker("^NSEI").history(period="max", auto_adjust=False)
    df = df.rename(columns=str.lower)
    if "adj close" in df.columns and "close" not in df.columns:
        df["close"] = df["adj close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[["open", "high", "low", "close", "volume"]]


def _audit_one_trade(
    trade: dict,
    df: pd.DataFrame,
    regime_series: pd.Series,
    industries: dict[str, str],
) -> dict:
    entry_ts = pd.Timestamp(trade["entry_date"])
    exit_ts = pd.Timestamp(trade["exit_date"])

    # Snap to nearest trading bar at or before the trade dates.
    entry_idx = df.index.get_indexer([entry_ts], method="pad")[0]
    exit_idx = df.index.get_indexer([exit_ts], method="pad")[0]
    if entry_idx < 0 or exit_idx < 0:
        return {"symbol": trade["symbol"], "_skipped": "no bar at entry/exit"}
    entry_bar = df.index[entry_idx]
    exit_bar = df.index[exit_idx]

    # Days from entry to stop (calendar days from the SimulatedTrade)
    days_to_stop = trade["days_held"]

    # Regime at entry / exit
    def _regime_at(ts: pd.Timestamp) -> str:
        idx = regime_series.index.get_indexer([ts], method="pad")[0]
        if idx < 0:
            return "Unknown"
        return str(regime_series.iloc[idx])

    regime_at_entry = _regime_at(entry_bar)
    regime_at_exit = _regime_at(exit_bar)
    regime_shifted = regime_at_entry != regime_at_exit

    # RVOL at entry
    rvol_series = rvol(df["volume"], 50)
    rvol_at_entry = float(rvol_series.iloc[entry_idx])

    # ATR(14) absolute and as % of close at entry
    atr_series = atr(df, 14)
    atr_at_entry = float(atr_series.iloc[entry_idx])
    close_at_entry = float(df["close"].iloc[entry_idx])
    atr_pct = (atr_at_entry / close_at_entry * 100.0) if close_at_entry > 0 else float("nan")

    # ATR percentile vs trailing 252-bar window (point-in-time)
    atr_window = atr_series.iloc[max(0, entry_idx - 252) : entry_idx]
    atr_percentile = (
        float((atr_window < atr_at_entry).mean() * 100.0)
        if len(atr_window) > 0
        else float("nan")
    )

    # Days since price last touched its 252-bar high (extension proxy)
    high_series = df["high"]
    high_252w = high_series.rolling(252, min_periods=60).max()
    past_highs = high_series.iloc[: entry_idx + 1]
    past_52w = high_252w.iloc[: entry_idx + 1]
    # "Touched 52WH" = high within 0.1% of the rolling-252 max
    touched_52wh = past_highs >= past_52w * 0.999
    if touched_52wh.any():
        last_touch_ts = past_highs[touched_52wh].index.max()
        days_since_52wh = int((entry_bar - last_touch_ts).days)
    else:
        days_since_52wh = None

    # Price action between entry and stop
    trade_window = df.iloc[entry_idx : exit_idx + 1]
    if len(trade_window) >= 2:
        max_close = float(trade_window["close"].max())
        min_close = float(trade_window["close"].min())
        max_fav_pct = (max_close / close_at_entry - 1.0) * 100.0
        max_adv_pct = (min_close / close_at_entry - 1.0) * 100.0
        daily_returns = trade_window["close"].pct_change().dropna()
        biggest_down_day_pct = float(daily_returns.min() * 100.0) if not daily_returns.empty else 0.0
    else:
        max_fav_pct = 0.0
        max_adv_pct = trade["return_pct"] * 100.0
        biggest_down_day_pct = trade["return_pct"] * 100.0

    return {
        "symbol": trade["symbol"],
        "sub_industry": industries.get(trade["symbol"], "—"),
        "entry_date": trade["entry_date"],
        "exit_date": trade["exit_date"],
        "days_to_stop": days_to_stop,
        "return_pct": trade["return_pct"] * 100.0,
        "regime_at_entry": regime_at_entry,
        "regime_at_exit": regime_at_exit,
        "regime_shifted": regime_shifted,
        "rvol_at_entry": rvol_at_entry,
        "atr_pct_of_close_at_entry": atr_pct,
        "atr_percentile_252b": atr_percentile,
        "days_since_52wh_at_entry": days_since_52wh,
        "max_fav_excursion_pct": max_fav_pct,
        "max_adv_excursion_pct": max_adv_pct,
        "biggest_down_day_pct": biggest_down_day_pct,
    }


# ──────────────────────────────────────────────────────────────────────────
# Cluster detection — buckets each feature, counts density, flags ≥25/41
# ──────────────────────────────────────────────────────────────────────────
def _bucket(value: float | None, edges: list[float], labels: list[str]) -> str:
    """Return the label for the bucket ``value`` falls into."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "—"
    for edge, label in zip(edges, labels[:-1], strict=False):
        if value <= edge:
            return label
    return labels[-1]


def _cluster_summary(rows: list[dict]) -> list[tuple[str, str, int, str]]:
    """Return list of (feature, bucket_label, count, density_marker)."""
    n = len(rows)
    out: list[tuple[str, str, int, str]] = []

    def add(feature: str, bucket: str, count: int) -> None:
        density = (
            f"**{count}/{n}**" if count >= CLUSTER_DENSITY_THRESHOLD else f"{count}/{n}"
        )
        out.append((feature, bucket, count, density))

    # days_to_stop buckets
    edges_dts = [3, 7, 14, 30]
    labels_dts = ["≤3 days", "4-7 days", "8-14 days", "15-30 days", ">30 days"]
    counts = Counter(_bucket(r["days_to_stop"], edges_dts, labels_dts) for r in rows)
    for label in labels_dts:
        if counts.get(label):
            add("days_to_stop", label, counts[label])

    # regime_at_entry
    counts = Counter(r["regime_at_entry"] for r in rows)
    for label in ["Risk_On", "Caution", "Risk_Off", "Unknown"]:
        if counts.get(label):
            add("regime_at_entry", label, counts[label])

    # regime_shifted
    shift_count = sum(1 for r in rows if r["regime_shifted"])
    add("regime_shifted_during_trade", "True", shift_count)

    # RVOL at entry buckets
    edges_rvol = [1.0, 1.5, 2.0, 3.0]
    labels_rvol = ["<1.0", "1.0-1.5", "1.5-2.0", "2.0-3.0", "≥3.0"]
    counts = Counter(_bucket(r["rvol_at_entry"], edges_rvol, labels_rvol) for r in rows)
    for label in labels_rvol:
        if counts.get(label):
            add("rvol_at_entry", label, counts[label])

    # ATR percentile (vol regime at entry)
    edges_atr = [25, 50, 75]
    labels_atr = ["bottom_quartile", "Q2", "Q3", "top_quartile"]
    counts = Counter(_bucket(r["atr_percentile_252b"], edges_atr, labels_atr) for r in rows)
    for label in labels_atr:
        if counts.get(label):
            add("atr_percentile_252b", label, counts[label])

    # Days since 52WH (extension proxy)
    edges_52wh = [5, 20, 60]
    labels_52wh = ["≤5 days (very extended)", "6-20 days", "21-60 days", ">60 days (mid-trend)"]
    counts = Counter(
        _bucket(r["days_since_52wh_at_entry"], edges_52wh, labels_52wh) for r in rows
    )
    for label in labels_52wh:
        if counts.get(label):
            add("days_since_52wh_at_entry", label, counts[label])

    # Sub-industry — flag any sub-industry with ≥ 5 trades
    sub_counts = Counter(r["sub_industry"] for r in rows)
    for sub, count in sub_counts.most_common():
        if count >= 5:
            add("sub_industry", sub, count)

    # Price action: sharp drop vs drift
    sharp = sum(1 for r in rows if (r["biggest_down_day_pct"] or 0) <= -3.0)
    drift = sum(1 for r in rows if (r["biggest_down_day_pct"] or 0) > -3.0)
    add("price_action", "sharp_drop_≥3pct_in_one_day", sharp)
    add("price_action", "drift_no_single_day_≥3pct", drift)

    return out


# ──────────────────────────────────────────────────────────────────────────
# Report rendering
# ──────────────────────────────────────────────────────────────────────────
def _render_report(
    rows: list[dict],
    clusters: list[tuple[str, str, int, str]],
) -> str:
    n = len(rows)
    lines: list[str] = []

    lines += [
        "# Phase G1 — A4 Stop-Out Audit",
        "",
        f"**Source:** A1 trade list (industrial-only Nifty 500, 3pct stop)",
        f"**Trades audited:** {n} of 41 STOP_HIT outcomes",
        f"**Generated:** {date.today().isoformat()}",
        f"**Cluster density threshold:** ≥ {CLUSTER_DENSITY_THRESHOLD} of {n} trades share a feature",
        "",
        "---",
        "",
        "## Per-trade audit",
        "",
        "| Symbol | Sub-industry | Entry | Exit | Days | Ret% | Regime In→Out | RVOL | ATR%c | ATR%ile | Days since 52WH | Max Fav | Max Adv | Biggest Down |",
        "|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(rows, key=lambda x: x["entry_date"]):
        regime_pair = (
            f"{r['regime_at_entry']}→{r['regime_at_exit']}"
            if r["regime_shifted"]
            else r["regime_at_entry"]
        )
        d52 = r["days_since_52wh_at_entry"]
        lines.append(
            f"| `{r['symbol']}` | {r['sub_industry']} | {r['entry_date']} | "
            f"{r['exit_date']} | {r['days_to_stop']} | {r['return_pct']:.2f} | "
            f"{regime_pair} | {r['rvol_at_entry']:.2f} | "
            f"{r['atr_pct_of_close_at_entry']:.2f} | {r['atr_percentile_252b']:.0f} | "
            f"{d52 if d52 is not None else '—'} | "
            f"{r['max_fav_excursion_pct']:+.2f} | {r['max_adv_excursion_pct']:+.2f} | "
            f"{r['biggest_down_day_pct']:.2f} |"
        )

    lines += [
        "",
        "## Cluster patterns identified",
        "",
        "Buckets where the share of stop-outs concentrates. **Bold** = density "
        f"≥ {CLUSTER_DENSITY_THRESHOLD}/{n} (the user-defined cluster threshold).",
        "",
        "| Feature | Bucket | Density |",
        "|---|---|---:|",
    ]
    for feature, bucket, _count, density in clusters:
        lines.append(f"| `{feature}` | {bucket} | {density} |")

    lines += [
        "",
        "## Diagnostic summary",
        "",
        f"- Median days to stop: {int(np.median([r['days_to_stop'] for r in rows]))}",
        f"- Median return: {np.median([r['return_pct'] for r in rows]):.2f}%",
        f"- Avg ATR % of close at entry: {np.mean([r['atr_pct_of_close_at_entry'] for r in rows]):.2f}%",
        f"- Avg ATR percentile at entry: {np.mean([r['atr_percentile_252b'] for r in rows]):.0f}",
        f"- Median days-since-52WH at entry: {int(np.median([r['days_since_52wh_at_entry'] or 0 for r in rows]))}",
        f"- Trades with regime shift during hold: {sum(1 for r in rows if r['regime_shifted'])}",
        f"- Trades with a single-bar drop ≥ 3%: {sum(1 for r in rows if (r['biggest_down_day_pct'] or 0) <= -3.0)}",
        "",
        "## Top hypotheses (ranked by density)",
        "",
    ]

    # Top 3 hypotheses by density. Filter out the trivial "all 41 in same
    # bucket because they all happen to be in regime X" — only keep
    # buckets that are NOT the entire dataset (count < n) and have density
    # ≥ 25/41.
    significant = [
        (feat, bucket, count)
        for feat, bucket, count, _ in clusters
        if count >= CLUSTER_DENSITY_THRESHOLD and count < n
    ]
    significant.sort(key=lambda t: -t[2])
    if significant:
        for i, (feat, bucket, count) in enumerate(significant[:3], 1):
            lines.append(
                f"{i}. **`{feat}` = {bucket}** in {count}/{n} trades. "
                f"Candidate filter: exclude entries that match this bucket."
            )
    else:
        lines.append(
            "No single feature concentrates ≥ "
            f"{CLUSTER_DENSITY_THRESHOLD}/{n} stop-outs. The pattern is "
            "diffuse — stop-outs look like irreducible variance across "
            "the audited features. This maps to the user's escalation "
            "branch: deliberate §11 calibration conversation rather "
            "than a new candidate filter rule."
        )

    lines += [
        "",
        "## Notes",
        "",
        "- Audit is point-in-time per trade — every feature is computed",
        "  using only data available at the entry bar (no lookahead).",
        "- ``ATR%c`` = ATR(14) as percentage of close at entry.",
        "- ``ATR%ile`` = entry-day ATR percentile vs trailing 252 bars.",
        "- ``Days since 52WH`` = calendar days since the bar where",
        "  high reached its trailing-252-bar maximum.",
        "- ``Max Fav / Max Adv`` = max favorable / adverse close excursion",
        "  during the trade window, as percent of entry price.",
        "- ``Biggest Down`` = largest single-bar percent drop during the",
        "  trade window.",
    ]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────
def main() -> int:
    if not TRADES_PATH.exists():
        print(f"ERROR: trades file missing at {TRADES_PATH}", file=sys.stderr)
        return 1

    trades = json.loads(TRADES_PATH.read_text())
    stopouts = [t for t in trades if t["outcome"] == "STOP_HIT"]
    print(
        f"Auditing {len(stopouts)} STOP_HIT trades from A1...",
        file=sys.stderr,
    )

    industries = _load_industries()
    nifty_df = _load_index()
    regime_series = market_regime(nifty_df)

    rows: list[dict] = []
    for trade in stopouts:
        try:
            df = load_eod(trade["symbol"])
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {trade['symbol']}: {exc}", file=sys.stderr)
            continue
        rows.append(
            _audit_one_trade(trade, df, regime_series, industries)
        )

    rows = [r for r in rows if not r.get("_skipped")]
    print(f"  audited {len(rows)}/{len(stopouts)}", file=sys.stderr)

    clusters = _cluster_summary(rows)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(_render_report(rows, clusters), encoding="utf-8")
    print(f"  wrote {REPORT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
