"""S1.7 acceptance demo — 5-row insert/query against the locked schema.

Boots an embedded Postgres 16 via :mod:`pgserver`, applies the §17/§25
schema, inserts five varied ledger entries (covering both cohorts in
the v1 §14a registry), opens two positions, runs a position through
the §25 state machine, and proves the append-only trigger blocks an
attempted UPDATE.

Run::

    python scripts/ledger_demo.py

Output is human-readable; intended as the stop-after-demo artefact for
the S1.7 acceptance review.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

# Allow ``python scripts/ledger_demo.py`` to import the filter package
# without requiring an editable install.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "filter"))

import pgserver  # noqa: E402
import psycopg  # noqa: E402

from saadhana_filter.cohorts import COHORTS, get_cohort  # noqa: E402
from saadhana_filter.ledger import (  # noqa: E402
    PositionRecord,
    SignalRecord,
    append_position_event,
    apply_schema,
    insert_position,
    insert_signal,
    read_position_lifecycle,
    update_position_state,
)


def _hr(title: str = "") -> None:
    print()
    print("─" * 72)
    if title:
        print(title)
        print("─" * 72)


def main() -> None:
    print("S1.7 — Postgres + Sec.17 ledger schema lock — acceptance demo")
    print(f"Repo: {REPO_ROOT}")

    _hr("§14a registry — Python source of truth (v1 ships 2 of 10 cohorts)")
    for c in COHORTS:
        print(
            f"  • {c.cohort_id:<22} status={c.status:<11} "
            f"tier={c.position_size_tier:<9} sector_excl={list(c.sector_exclusions) or '[]'}"
        )

    data_dir = Path(tempfile.mkdtemp(prefix="saadhana_demo_pg_"))
    server = pgserver.get_server(data_dir)
    try:
        uri = server.get_uri()
        _hr("Embedded Postgres up")
        print(f"  uri: {uri}")

        with psycopg.connect(uri) as conn:
            _hr("Applying locked schema")
            apply_schema(conn)

            with conn.cursor() as cur:
                cur.execute(
                    """
                    select table_name
                      from information_schema.tables
                     where table_schema='public' and table_type='BASE TABLE'
                     order by table_name
                    """
                )
                tables = [r[0] for r in cur.fetchall()]
            print(f"  tables created: {tables}")
            assert tables == ["position_events", "positions", "signals_ledger"]

            # ────────────────────────────────────────────────────────
            # 5-row insert into signals_ledger (mix of cohorts)
            # ────────────────────────────────────────────────────────
            _hr("Inserting 5 signals into signals_ledger")
            pro = get_cohort("pro_setup_13")
            tc = get_cohort("triple_confluence")
            samples = [
                SignalRecord(
                    signal_id="sig_2026_05_02_DIVISLAB_001",
                    spec_version="2.1",
                    cohort_id=pro.cohort_id,
                    sector_exclusions=pro.sector_exclusions,
                    symbol="DIVISLAB",
                    signal_date=date(2026, 5, 2),
                    signal_price=6234.50,
                    regime="Risk_On",
                    sector="HEALTHCARE",
                    conviction=31.2,
                    conviction_tier="HIGH",
                    payload={"pro_setup_score": 13, "downside_resistance_score": 78},
                ),
                SignalRecord(
                    signal_id="sig_2026_05_02_LT_001",
                    spec_version="2.1",
                    cohort_id=pro.cohort_id,
                    sector_exclusions=pro.sector_exclusions,
                    symbol="LT",
                    signal_date=date(2026, 5, 2),
                    signal_price=3712.40,
                    regime="Risk_On",
                    sector="INFRASTRUCTURE",
                    conviction=24.0,
                    conviction_tier="STANDARD",
                    payload={"pro_setup_score": 13, "downside_resistance_score": 71},
                ),
                SignalRecord(
                    signal_id="sig_2026_05_02_TITAN_001",
                    spec_version="2.1",
                    cohort_id=tc.cohort_id,
                    sector_exclusions=tc.sector_exclusions,
                    symbol="TITAN",
                    signal_date=date(2026, 5, 2),
                    signal_price=3520.80,
                    regime="Risk_On",
                    sector="CONSUMER_DISCRETIONARY",
                    conviction=None,
                    conviction_tier="HIGH",  # 3-of-3 Triple confluence
                    payload={
                        "triple_confluence_score": 3,
                        "agreeing_components": [
                            "ma_crossover",
                            "adaptive_st",
                            "deviation_trend",
                        ],
                    },
                ),
                SignalRecord(
                    signal_id="sig_2026_05_02_INFY_001",
                    spec_version="2.1",
                    cohort_id=tc.cohort_id,
                    sector_exclusions=tc.sector_exclusions,
                    symbol="INFY",
                    signal_date=date(2026, 5, 2),
                    signal_price=1487.20,
                    regime="Risk_On",
                    sector="IT",
                    conviction=None,
                    conviction_tier="STANDARD",  # 2-of-3 Triple confluence
                    payload={
                        "triple_confluence_score": 2,
                        "agreeing_components": ["ma_crossover", "adaptive_st"],
                    },
                ),
                SignalRecord(
                    signal_id="sig_2026_05_02_BHARTIARTL_001",
                    spec_version="2.1",
                    cohort_id=pro.cohort_id,
                    sector_exclusions=pro.sector_exclusions,
                    symbol="BHARTIARTL",
                    signal_date=date(2026, 5, 2),
                    signal_price=1452.10,
                    regime="Risk_On",
                    sector="TELECOM",
                    conviction=18.5,
                    conviction_tier="WATCH",
                    payload={"pro_setup_score": 11, "downside_resistance_score": 64},
                ),
            ]
            for s in samples:
                insert_signal(conn, s)
                print(
                    f"  + {s.signal_id:<35} {s.cohort_id:<18} "
                    f"{s.symbol:<12} ₹{float(s.signal_price):>8.2f}  tier={s.conviction_tier}"
                )

            _hr("Querying — top 3 by signal_price (desc), cohort breakdown")
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select symbol, cohort_id, signal_price, conviction_tier
                      from signals_ledger
                     where signal_date = %s
                     order by signal_price desc
                     limit 3
                    """,
                    (date(2026, 5, 2),),
                )
                for sym, coh, price, tier in cur.fetchall():
                    print(f"  {sym:<12} {coh:<18} ₹{float(price):>8.2f}  {tier}")

                cur.execute(
                    """
                    select cohort_id, count(*) as n
                      from signals_ledger
                     group by cohort_id
                     order by cohort_id
                    """
                )
                print()
                print("  cohort breakdown:")
                for coh, n in cur.fetchall():
                    print(f"    {coh:<22} {n}")

            # ────────────────────────────────────────────────────────
            # Open positions for two of the signals; advance state
            # ────────────────────────────────────────────────────────
            _hr("Opening 2 positions; running 1 through the §25 state machine")
            pos1_id = insert_position(
                conn,
                PositionRecord(
                    signal_id="sig_2026_05_02_DIVISLAB_001",
                    cohort_id="pro_setup_13",
                    symbol="DIVISLAB",
                    entry_date=date(2026, 5, 3),
                    entry_price=6240.00,
                    entry_stop=6075.00,
                    target_t1=6546.23,
                    target_t2=6858.95,
                    target_t3=7150.00,
                    size_qty=15,
                ),
            )
            pos2_id = insert_position(
                conn,
                PositionRecord(
                    signal_id="sig_2026_05_02_TITAN_001",
                    cohort_id="triple_confluence",
                    symbol="TITAN",
                    entry_date=date(2026, 5, 3),
                    entry_price=3528.20,
                    entry_stop=3422.00,
                    target_t1=3704.61,
                    target_t2=3881.02,
                    target_t3=4057.43,
                    size_qty=22,
                ),
            )
            print(f"  position #1: DIVISLAB → {pos1_id}")
            print(f"  position #2: TITAN    → {pos2_id}")

            # State transitions on DIVISLAB.
            for bar_date, frm, to, reason in [
                (date(2026, 5, 6), "HEALTHY", "AT_RISK", "DTS_LT_1ATR"),
                (date(2026, 5, 8), "AT_RISK", "HEALTHY", "PULLED_BACK"),
                (date(2026, 5, 12), "HEALTHY", "TARGET_NEAR", "WITHIN_HALF_ATR"),
                (date(2026, 5, 13), "TARGET_NEAR", "TRIGGERED", "TARGET_T1"),
                (date(2026, 5, 13), "TRIGGERED", "CLOSED", "TARGET_T1"),
            ]:
                append_position_event(
                    conn,
                    position_id=pos1_id,
                    bar_date=bar_date,
                    from_state=frm,
                    to_state=to,
                    reason=reason,
                    cohort_id="pro_setup_13",
                )
            update_position_state(
                conn,
                pos1_id,
                state="CLOSED",
                exit_date=date(2026, 5, 13),
                exit_price=6546.23,
                exit_trigger="TARGET_T1",
                exit_outcome="WIN_T1",
            )

            lifecycle = read_position_lifecycle(conn, pos1_id)
            print(
                f"  DIVISLAB final: state={lifecycle['position']['state']}  "
                f"trigger={lifecycle['position']['exit_trigger']}  "
                f"outcome={lifecycle['position']['exit_outcome']}  "
                f"events={len(lifecycle['events'])}"
            )
            for e in lifecycle["events"]:
                print(
                    f"    {e['bar_date']}  {e['from_state']:<11} → {e['to_state']:<11} "
                    f"reason={e['reason']}"
                )

            # ────────────────────────────────────────────────────────
            # Append-only enforcement — both UPDATE and DELETE blocked
            # ────────────────────────────────────────────────────────
            _hr("Verifying DB-level append-only enforcement")
            for op_label, sql, params in [
                (
                    "UPDATE on signals_ledger",
                    "update signals_ledger set conviction_tier='STANDARD' where signal_id=%s",
                    ("sig_2026_05_02_DIVISLAB_001",),
                ),
                (
                    "DELETE on signals_ledger",
                    "delete from signals_ledger where signal_id=%s",
                    ("sig_2026_05_02_DIVISLAB_001",),
                ),
                (
                    "UPDATE on position_events",
                    "update position_events set reason='rewritten' where event_id=1",
                    None,
                ),
            ]:
                try:
                    with conn.cursor() as cur:
                        if params:
                            cur.execute(sql, params)
                        else:
                            cur.execute(sql)
                    raise AssertionError(f"{op_label} did NOT raise — trigger missing!")
                except psycopg.errors.CheckViolation as ex:
                    conn.rollback()
                    msg = str(ex).splitlines()[0]
                    print(f"  ✓ {op_label} blocked: {msg}")

            # Confirm the row is still HIGH (rollback cleared the attempt).
            with conn.cursor() as cur:
                cur.execute(
                    "select conviction_tier from signals_ledger where signal_id = %s",
                    ("sig_2026_05_02_DIVISLAB_001",),
                )
                tier_after = cur.fetchone()[0]
            print(f"  Original DIVISLAB conviction_tier post-attack: {tier_after}")
            assert tier_after == "HIGH"

            _hr("Final row counts")
            with conn.cursor() as cur:
                for tbl in ("signals_ledger", "positions", "position_events"):
                    cur.execute(f"select count(*) from {tbl}")
                    print(f"  {tbl:<18} {cur.fetchone()[0]}")

        print()
        print("S1.7 demo complete — schema locked, append-only enforced, "
              "lifecycle reconstructible.")
    finally:
        server.cleanup()
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
