-- ====================================================================
-- §17 Signal Ledger + §25 Position state — Postgres schema (S1.7 lock)
-- ====================================================================
-- The S1.7 lock covers exactly THREE tables: signals_ledger,
-- positions, position_events. Other tables (forensics_results,
-- daily_reports, learning_feedback, etc.) are deferred to their own
-- sprints per §17.3.
--
-- Append-only enforcement is at the DB level (trigger), not in app
-- code — see saadhana_block_mutation() at the bottom.
--
-- gen_random_uuid() is core in PostgreSQL 13+ (no extension needed).
-- Vercel Postgres ships PG15+; pgserver bundles PG16 — both qualify.

-- --------------------------------------------------------------------
-- signals_ledger — every BUY ever issued, append-only
-- --------------------------------------------------------------------
create table if not exists signals_ledger (
    signal_id           text          primary key,
    spec_version        text          not null,
    cohort_id           text          not null,
    sector_exclusions   jsonb         not null default '[]'::jsonb,
    symbol              text          not null,
    signal_date         date          not null,
    signal_price        numeric(18,4) not null,
    regime              text,
    sector              text,
    conviction          numeric(10,4),
    conviction_tier     text,
    payload             jsonb         not null,
    created_at          timestamptz   not null default now()
);
create index if not exists ix_signals_ledger_symbol_date
    on signals_ledger (symbol, signal_date desc);
create index if not exists ix_signals_ledger_cohort_date
    on signals_ledger (cohort_id, signal_date desc);

-- --------------------------------------------------------------------
-- positions — one row per held position; mutable on state/exit
-- --------------------------------------------------------------------
create table if not exists positions (
    position_id     uuid          primary key default gen_random_uuid(),
    signal_id       text          not null references signals_ledger(signal_id),
    cohort_id       text          not null,
    symbol          text          not null,
    entry_date      date          not null,
    entry_price     numeric(18,4) not null,
    entry_stop      numeric(18,4) not null,
    target_t1       numeric(18,4),
    target_t2       numeric(18,4),
    target_t3       numeric(18,4),
    size_qty        integer       not null,
    state           text          not null default 'HEALTHY',
    exit_date       date,
    exit_price      numeric(18,4),
    exit_trigger    text,
    exit_outcome    text,
    created_at      timestamptz   not null default now(),
    updated_at      timestamptz   not null default now(),
    constraint positions_state_chk check (state in
        ('HEALTHY','AT_RISK','TARGET_NEAR','TRIGGERED','CLOSED','PAUSED'))
);
create index if not exists ix_positions_symbol on positions (symbol);
create index if not exists ix_positions_open
    on positions (state) where state <> 'CLOSED';
create index if not exists ix_positions_cohort on positions (cohort_id);

-- --------------------------------------------------------------------
-- position_events — per-bar audit log from §25; append-only
-- --------------------------------------------------------------------
create table if not exists position_events (
    event_id        bigserial    primary key,
    position_id     uuid         not null references positions(position_id),
    bar_date        date         not null,
    from_state      text         not null,
    to_state        text         not null,
    reason          text         not null,
    cohort_id       text         not null,
    metadata        jsonb        not null default '{}'::jsonb,
    created_at      timestamptz  not null default now()
);
create index if not exists ix_position_events_position_bar
    on position_events (position_id, bar_date, created_at);
create index if not exists ix_position_events_cohort_bar
    on position_events (cohort_id, bar_date desc);

-- --------------------------------------------------------------------
-- Append-only enforcement — DB-level trigger
-- --------------------------------------------------------------------
create or replace function saadhana_block_mutation() returns trigger
language plpgsql as $$
begin
    raise exception
        'append-only table %: % is forbidden (signal_id/event_id immutable)',
        tg_table_name, tg_op
        using errcode = 'check_violation';
end;
$$;

drop trigger if exists trg_signals_ledger_no_update on signals_ledger;
drop trigger if exists trg_signals_ledger_no_delete on signals_ledger;
create trigger trg_signals_ledger_no_update
    before update on signals_ledger
    for each row execute function saadhana_block_mutation();
create trigger trg_signals_ledger_no_delete
    before delete on signals_ledger
    for each row execute function saadhana_block_mutation();

drop trigger if exists trg_position_events_no_update on position_events;
drop trigger if exists trg_position_events_no_delete on position_events;
create trigger trg_position_events_no_update
    before update on position_events
    for each row execute function saadhana_block_mutation();
create trigger trg_position_events_no_delete
    before delete on position_events
    for each row execute function saadhana_block_mutation();

-- positions table is intentionally MUTABLE — state advances HEALTHY
-- → AT_RISK → CLOSED on the same row. Audit history of those
-- transitions lives in position_events, which IS append-only.

-- --------------------------------------------------------------------
-- updated_at maintenance for positions (mutable rows)
-- --------------------------------------------------------------------
create or replace function saadhana_touch_updated_at() returns trigger
language plpgsql as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists trg_positions_touch_updated_at on positions;
create trigger trg_positions_touch_updated_at
    before update on positions
    for each row execute function saadhana_touch_updated_at();
