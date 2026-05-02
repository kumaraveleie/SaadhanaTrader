"""Tests for §17 + §25 Postgres ledger lock (S1.7).

The fixture spins up an embedded Postgres 16 via :mod:`pgserver` once
per session, and resets the schema between cases — so the suite is
fully self-contained (no external Postgres required).

Test surface (the operator-mandated 5+ for the S1.7 acceptance):

1. ``test_apply_schema_creates_three_tables`` — the lock is exactly
   three tables, no more, no less.
2. ``test_signals_ledger_insert_and_read`` — round-trip the §17
   payload column.
3. ``test_signals_ledger_update_blocked_by_trigger`` — append-only
   enforcement (the load-bearing DB invariant).
4. ``test_signals_ledger_delete_blocked_by_trigger`` — same, for DELETE.
5. ``test_position_events_append_only_blocks_update_and_delete`` —
   §25 audit log carries the same DB-level append-only guarantee.
6. ``test_positions_state_transitions_succeed`` — positions IS
   mutable (state machine), proves the trigger does not over-block.
7. ``test_position_lifecycle_reconstruction`` — events ordered by
   (bar_date, created_at) per §25 audit-completeness rule.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest

from saadhana_filter.ledger import (
    PositionRecord,
    SignalRecord,
    append_position_event,
    apply_schema,
    drop_schema,
    insert_position,
    insert_signal,
    read_position_lifecycle,
    update_position_state,
)


# ──────────────────────────────────────────────────────────────────────
# Embedded-Postgres fixture (pgserver)
# ──────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def pg_uri() -> Iterator[str]:
    """One embedded Postgres per test session.

    pgserver lays down a persistent data dir; we use a temp dir so
    the fixture cleans up automatically. Tests that need a clean
    schema use the ``conn`` fixture which drops + reapplies between
    cases.
    """
    pgserver = pytest.importorskip("pgserver")
    data_dir = Path(tempfile.mkdtemp(prefix="saadhana_pg_"))
    server = pgserver.get_server(data_dir)
    try:
        yield server.get_uri()
    finally:
        server.cleanup()
        # pgserver leaves the data dir on cleanup() in some builds;
        # remove explicitly so the test session leaves no residue.
        shutil.rmtree(data_dir, ignore_errors=True)


@pytest.fixture
def conn(pg_uri: str) -> Iterator[psycopg.Connection]:
    """A fresh connection with the locked schema applied. The schema
    is dropped + reapplied between tests so each case starts empty."""
    with psycopg.connect(pg_uri) as c:
        # Reset to a clean slate.
        try:
            drop_schema(c)
        except psycopg.errors.UndefinedTable:
            c.rollback()  # first run — nothing to drop
        apply_schema(c)
        yield c


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────
def _make_signal(
    *,
    signal_id: str = "sig_2026_05_02_DIVISLAB_001",
    cohort_id: str = "pro_setup_13",
    symbol: str = "DIVISLAB",
    sector_exclusions: tuple[str, ...] = ("FINANCIAL_SERVICES", "NBFC", "BANK"),
) -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        spec_version="2.1",
        cohort_id=cohort_id,
        sector_exclusions=sector_exclusions,
        symbol=symbol,
        signal_date=date(2026, 5, 2),
        signal_price=6234.50,
        regime="Risk_On",
        sector="HEALTHCARE",
        conviction=31.2,
        conviction_tier="HIGH",
        payload={
            "pro_setup_score": 13,
            "downside_resistance_score": 78,
            "indicators_snapshot": {"rsi_14": 64.2, "atr_14": 142.3},
        },
    )


def _make_position(signal_id: str, symbol: str = "DIVISLAB") -> PositionRecord:
    return PositionRecord(
        signal_id=signal_id,
        cohort_id="pro_setup_13",
        symbol=symbol,
        entry_date=date(2026, 5, 3),
        entry_price=6240.00,
        entry_stop=6075.00,
        target_t1=6546.23,
        target_t2=6858.95,
        target_t3=7150.00,
        size_qty=15,
    )


# ──────────────────────────────────────────────────────────────────────
# 1. Schema shape — exactly three locked tables
# ──────────────────────────────────────────────────────────────────────
def test_apply_schema_creates_three_tables(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            select table_name
              from information_schema.tables
             where table_schema = 'public'
               and table_type = 'BASE TABLE'
             order by table_name
            """
        )
        tables = [r[0] for r in cur.fetchall()]
    assert tables == ["position_events", "positions", "signals_ledger"], (
        "S1.7 lock is exactly three tables; found: " + ", ".join(tables)
    )


# ──────────────────────────────────────────────────────────────────────
# 2. signals_ledger round-trip
# ──────────────────────────────────────────────────────────────────────
def test_signals_ledger_insert_and_read(conn: psycopg.Connection) -> None:
    sig = _make_signal()
    returned = insert_signal(conn, sig)
    assert returned == sig.signal_id

    with conn.cursor() as cur:
        cur.execute(
            """
            select symbol, cohort_id, signal_price, conviction_tier,
                   sector_exclusions, payload
              from signals_ledger
             where signal_id = %s
            """,
            (sig.signal_id,),
        )
        row = cur.fetchone()
    assert row is not None
    symbol, cohort, price, tier, exclusions, payload = row
    assert symbol == "DIVISLAB"
    assert cohort == "pro_setup_13"
    assert float(price) == 6234.50
    assert tier == "HIGH"
    assert exclusions == ["FINANCIAL_SERVICES", "NBFC", "BANK"]
    assert payload["pro_setup_score"] == 13
    assert payload["indicators_snapshot"]["rsi_14"] == 64.2


# ──────────────────────────────────────────────────────────────────────
# 3 & 4. Append-only enforcement (UPDATE / DELETE both blocked)
# ──────────────────────────────────────────────────────────────────────
def test_signals_ledger_update_blocked_by_trigger(conn: psycopg.Connection) -> None:
    sig = _make_signal()
    insert_signal(conn, sig)

    # The trigger raises with SQLSTATE 23514 (check_violation) so
    # psycopg surfaces CheckViolation. The message is what the
    # operator-facing error ultimately renders.
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        with conn.cursor() as cur:
            cur.execute(
                "update signals_ledger set conviction_tier = 'STANDARD' where signal_id = %s",
                (sig.signal_id,),
            )
    assert "append-only" in str(exc.value).lower()
    conn.rollback()  # surface the failed transaction

    # Confirm the original row is intact post-rollback.
    with conn.cursor() as cur:
        cur.execute(
            "select conviction_tier from signals_ledger where signal_id = %s",
            (sig.signal_id,),
        )
        assert cur.fetchone()[0] == "HIGH"


def test_signals_ledger_delete_blocked_by_trigger(conn: psycopg.Connection) -> None:
    sig = _make_signal()
    insert_signal(conn, sig)

    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        with conn.cursor() as cur:
            cur.execute(
                "delete from signals_ledger where signal_id = %s",
                (sig.signal_id,),
            )
    assert "append-only" in str(exc.value).lower()
    conn.rollback()

    with conn.cursor() as cur:
        cur.execute(
            "select count(*) from signals_ledger where signal_id = %s",
            (sig.signal_id,),
        )
        assert cur.fetchone()[0] == 1


# ──────────────────────────────────────────────────────────────────────
# 5. position_events — same append-only guarantee
# ──────────────────────────────────────────────────────────────────────
def test_position_events_append_only_blocks_update_and_delete(conn: psycopg.Connection) -> None:
    sig = _make_signal()
    insert_signal(conn, sig)
    pos = _make_position(sig.signal_id)
    pid = insert_position(conn, pos)

    eid = append_position_event(
        conn,
        position_id=pid,
        bar_date=date(2026, 5, 4),
        from_state="HEALTHY",
        to_state="AT_RISK",
        reason="DTS_LT_1ATR",
        cohort_id="pro_setup_13",
        metadata={"distance_to_stop_atr": 0.85},
    )

    # UPDATE blocked.
    with pytest.raises(psycopg.errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute(
                "update position_events set reason = 'rewritten' where event_id = %s",
                (eid,),
            )
    conn.rollback()

    # DELETE blocked.
    with pytest.raises(psycopg.errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute(
                "delete from position_events where event_id = %s",
                (eid,),
            )
    conn.rollback()

    # Row still present, unchanged.
    with conn.cursor() as cur:
        cur.execute(
            "select reason from position_events where event_id = %s",
            (eid,),
        )
        assert cur.fetchone()[0] == "DTS_LT_1ATR"


# ──────────────────────────────────────────────────────────────────────
# 6. positions IS mutable — proves the trigger doesn't over-block
# ──────────────────────────────────────────────────────────────────────
def test_positions_state_transitions_succeed(conn: psycopg.Connection) -> None:
    sig = _make_signal()
    insert_signal(conn, sig)
    pid = insert_position(conn, _make_position(sig.signal_id))

    # Step through HEALTHY → AT_RISK → CLOSED.
    update_position_state(conn, pid, state="AT_RISK")
    update_position_state(
        conn,
        pid,
        state="CLOSED",
        exit_date=date(2026, 5, 18),
        exit_price=6450.00,
        exit_trigger="TARGET_T1",
        exit_outcome="WIN_T1",
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            select state, exit_trigger, exit_outcome, exit_price,
                   updated_at > created_at as touched
              from positions
             where position_id = %s
            """,
            (str(pid),),
        )
        row = cur.fetchone()
    state, trigger, outcome, exit_price, touched = row
    assert state == "CLOSED"
    assert trigger == "TARGET_T1"
    assert outcome == "WIN_T1"
    assert float(exit_price) == 6450.00
    assert touched is True, "updated_at trigger must advance on UPDATE"


# ──────────────────────────────────────────────────────────────────────
# 7. Lifecycle reconstruction — events ordered (bar_date, created_at)
# ──────────────────────────────────────────────────────────────────────
def test_position_lifecycle_reconstruction(conn: psycopg.Connection) -> None:
    sig = _make_signal()
    insert_signal(conn, sig)
    pid = insert_position(conn, _make_position(sig.signal_id))

    bars = [
        (date(2026, 5, 4), "HEALTHY", "AT_RISK", "DTS_LT_1ATR"),
        (date(2026, 5, 5), "AT_RISK", "HEALTHY", "PULLED_BACK"),
        (date(2026, 5, 11), "HEALTHY", "TARGET_NEAR", "WITHIN_HALF_ATR"),
        (date(2026, 5, 12), "TARGET_NEAR", "TRIGGERED", "TARGET_T1"),
        (date(2026, 5, 12), "TRIGGERED", "CLOSED", "TARGET_T1"),
    ]
    for bar_date, frm, to, reason in bars:
        append_position_event(
            conn,
            position_id=pid,
            bar_date=bar_date,
            from_state=frm,
            to_state=to,
            reason=reason,
            cohort_id="pro_setup_13",
        )

    update_position_state(
        conn,
        pid,
        state="CLOSED",
        exit_date=date(2026, 5, 12),
        exit_price=6546.23,
        exit_trigger="TARGET_T1",
        exit_outcome="WIN_T1",
    )

    lifecycle = read_position_lifecycle(conn, pid)
    assert lifecycle["position"]["state"] == "CLOSED"
    assert lifecycle["position"]["exit_outcome"] == "WIN_T1"

    events = lifecycle["events"]
    assert len(events) == 5
    expected_order = [
        ("HEALTHY", "AT_RISK"),
        ("AT_RISK", "HEALTHY"),
        ("HEALTHY", "TARGET_NEAR"),
        ("TARGET_NEAR", "TRIGGERED"),
        ("TRIGGERED", "CLOSED"),
    ]
    actual_order = [(e["from_state"], e["to_state"]) for e in events]
    assert actual_order == expected_order, (
        "events must be ordered by (bar_date, created_at) per §25 audit rule"
    )

    # Same-day events (the last two are both 2026-05-12) must preserve
    # insertion order — created_at is the secondary key.
    same_day = [e for e in events if e["bar_date"] == date(2026, 5, 12)]
    assert len(same_day) == 2
    assert same_day[0]["from_state"] == "TARGET_NEAR"
    assert same_day[1]["from_state"] == "TRIGGERED"
