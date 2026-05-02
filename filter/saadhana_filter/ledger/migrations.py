"""Schema apply / drop helpers for the §17 + §25 ledger lock.

The DDL itself lives in :data:`SCHEMA_PATH` so it can be applied by
both Python (``apply_schema(conn)``) and the ``psql -f`` CLI without
divergence.
"""

from __future__ import annotations

from pathlib import Path

import psycopg

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def read_schema_sql() -> str:
    """Return the full DDL text used by both Python migrations and CLI
    application. Centralised so callers can't accidentally diverge."""
    return SCHEMA_PATH.read_text(encoding="utf-8")


def apply_schema(conn: psycopg.Connection) -> None:
    """Apply the locked schema to ``conn`` (idempotent — every DDL
    statement uses ``if not exists`` / ``create or replace`` so
    re-applying after S2.x writer changes is safe).
    """
    sql = read_schema_sql()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def drop_schema(conn: psycopg.Connection) -> None:
    """Tear down the three locked tables — used by tests between
    cases and by operators when bootstrapping a fresh test DB.
    Production NEVER calls this; the §17 ledger is by definition
    append-only across the system's lifetime.
    """
    statements = [
        "drop trigger if exists trg_signals_ledger_no_update on signals_ledger",
        "drop trigger if exists trg_signals_ledger_no_delete on signals_ledger",
        "drop trigger if exists trg_position_events_no_update on position_events",
        "drop trigger if exists trg_position_events_no_delete on position_events",
        "drop trigger if exists trg_positions_touch_updated_at on positions",
        "drop table if exists position_events cascade",
        "drop table if exists positions cascade",
        "drop table if exists signals_ledger cascade",
        "drop function if exists saadhana_block_mutation()",
        "drop function if exists saadhana_touch_updated_at()",
    ]
    with conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt)
    conn.commit()
