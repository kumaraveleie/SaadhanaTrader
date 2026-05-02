"""Insert + read helpers for the §17 ledger and §25 position tables.

These are thin wrappers over psycopg — no ORM, no abstraction layer
beyond what the schema requires. Append-only is enforced at the DB
level (``saadhana_block_mutation`` trigger), not here. App code that
*intends* to update ``signals_ledger`` or ``position_events`` will
get a ``check_violation`` from Postgres regardless of which writer
function it calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb


@dataclass
class SignalRecord:
    """A row destined for ``signals_ledger`` — one per emitted signal.

    The ``payload`` carries the full §17 JSON snapshot (conditions,
    indicators, fundamentals, conviction); the named columns are the
    minimum subset the runtime needs for indexed queries.
    """

    signal_id: str
    spec_version: str
    cohort_id: str
    symbol: str
    signal_date: date
    signal_price: Decimal | float
    payload: dict[str, Any]
    sector_exclusions: tuple[str, ...] = field(default_factory=tuple)
    regime: str | None = None
    sector: str | None = None
    conviction: Decimal | float | None = None
    conviction_tier: str | None = None


@dataclass
class PositionRecord:
    """A row destined for ``positions``. ``state`` defaults to
    ``HEALTHY`` matching the §25 entry-bar default."""

    signal_id: str
    cohort_id: str
    symbol: str
    entry_date: date
    entry_price: Decimal | float
    entry_stop: Decimal | float
    size_qty: int
    target_t1: Decimal | float | None = None
    target_t2: Decimal | float | None = None
    target_t3: Decimal | float | None = None
    state: str = "HEALTHY"


def insert_signal(conn: psycopg.Connection, sig: SignalRecord) -> str:
    """INSERT a row into ``signals_ledger``. Returns the ``signal_id``
    on success; raises ``UniqueViolation`` if the id already exists
    (the ledger is append-only — re-emitting the same signal_id is
    forbidden by primary key, separately from the trigger that blocks
    updates/deletes).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into signals_ledger (
                signal_id, spec_version, cohort_id, sector_exclusions,
                symbol, signal_date, signal_price,
                regime, sector, conviction, conviction_tier, payload
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning signal_id
            """,
            (
                sig.signal_id,
                sig.spec_version,
                sig.cohort_id,
                Jsonb(list(sig.sector_exclusions)),
                sig.symbol,
                sig.signal_date,
                sig.signal_price,
                sig.regime,
                sig.sector,
                sig.conviction,
                sig.conviction_tier,
                Jsonb(sig.payload),
            ),
        )
        row = cur.fetchone()
    conn.commit()
    return row[0]


def insert_position(conn: psycopg.Connection, pos: PositionRecord) -> UUID:
    """INSERT a row into ``positions``. Returns the generated
    ``position_id``. The §17 row referenced by ``signal_id`` must
    already exist (FK constraint)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into positions (
                signal_id, cohort_id, symbol, entry_date,
                entry_price, entry_stop,
                target_t1, target_t2, target_t3,
                size_qty, state
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning position_id
            """,
            (
                pos.signal_id,
                pos.cohort_id,
                pos.symbol,
                pos.entry_date,
                pos.entry_price,
                pos.entry_stop,
                pos.target_t1,
                pos.target_t2,
                pos.target_t3,
                pos.size_qty,
                pos.state,
            ),
        )
        row = cur.fetchone()
    conn.commit()
    return row[0]


def update_position_state(
    conn: psycopg.Connection,
    position_id: UUID | str,
    *,
    state: str,
    exit_date: date | None = None,
    exit_price: Decimal | float | None = None,
    exit_trigger: str | None = None,
    exit_outcome: str | None = None,
) -> None:
    """Advance a position row's state. Only the mutable subset
    (``state``, ``exit_*``) can be touched here — the trigger on
    ``positions`` updates ``updated_at`` automatically.

    This function is the ONLY supported path for position mutation;
    callers that try to update entry_price or size_qty get a
    syntactic 'no such column in set list' from this function (and
    would in any case be doing something wrong)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            update positions
               set state        = %s,
                   exit_date    = coalesce(%s, exit_date),
                   exit_price   = coalesce(%s, exit_price),
                   exit_trigger = coalesce(%s, exit_trigger),
                   exit_outcome = coalesce(%s, exit_outcome)
             where position_id  = %s
            """,
            (state, exit_date, exit_price, exit_trigger, exit_outcome, str(position_id)),
        )
    conn.commit()


def append_position_event(
    conn: psycopg.Connection,
    *,
    position_id: UUID | str,
    bar_date: date,
    from_state: str,
    to_state: str,
    reason: str,
    cohort_id: str,
    metadata: dict[str, Any] | None = None,
) -> int:
    """INSERT a row into ``position_events`` (the §25 audit trail).
    Returns the auto-incremented ``event_id``."""
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into position_events (
                position_id, bar_date, from_state, to_state,
                reason, cohort_id, metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s)
            returning event_id
            """,
            (
                str(position_id),
                bar_date,
                from_state,
                to_state,
                reason,
                cohort_id,
                Jsonb(metadata or {}),
            ),
        )
        row = cur.fetchone()
    conn.commit()
    return row[0]


def read_position_lifecycle(
    conn: psycopg.Connection, position_id: UUID | str
) -> dict[str, Any]:
    """Return a position's current row + its full event history.

    Used by /positions UI and §25 forensics to reconstruct a
    position's transition timeline. Events are ordered by
    ``(bar_date, created_at)`` per §25 audit-completeness rule.
    """
    with conn.cursor() as cur:
        cur.execute(
            "select * from positions where position_id = %s",
            (str(position_id),),
        )
        pos_row = cur.fetchone()
        if pos_row is None:
            raise KeyError(f"position not found: {position_id}")
        pos_cols = [d.name for d in cur.description]

        cur.execute(
            """
            select event_id, bar_date, from_state, to_state, reason,
                   cohort_id, metadata, created_at
              from position_events
             where position_id = %s
             order by bar_date asc, created_at asc, event_id asc
            """,
            (str(position_id),),
        )
        evt_rows = cur.fetchall()
        evt_cols = [d.name for d in cur.description]

    return {
        "position": dict(zip(pos_cols, pos_row, strict=True)),
        "events": [dict(zip(evt_cols, r, strict=True)) for r in evt_rows],
    }


__all__ = [
    "PositionRecord",
    "SignalRecord",
    "append_position_event",
    "insert_position",
    "insert_signal",
    "read_position_lifecycle",
    "update_position_state",
]
