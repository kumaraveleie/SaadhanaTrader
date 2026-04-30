'use client';

import { useMemo, useState } from 'react';
import { useTheme } from '../components/theme';
import type { LifecycleTag as LifecycleTagType, ResearchRow } from '../lib/scan-types';
import { LifecycleTag } from './lifecycle-tag';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export type Column<T> = {
  key: string;
  label: string;
  tooltip?: string;
  align: 'left' | 'right';
  sortValue: (row: T) => number | string;
  cell: (row: T) => React.ReactNode;
  sortable?: boolean; // default true
};

type SortState = { key: string; dir: 'asc' | 'desc' } | null;

export function SortableTable<T>({
  columns,
  rows,
  getRowKey,
  initialSort,
  emptyState,
}: {
  columns: Column<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  initialSort?: SortState;
  emptyState?: React.ReactNode;
}) {
  const { t } = useTheme();
  const [sort, setSort] = useState<SortState>(initialSort ?? null);
  const [hovered, setHovered] = useState<string | null>(null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col) return rows;
    const arr = [...rows];
    arr.sort((a, b) => {
      const av = col.sortValue(a);
      const bv = col.sortValue(b);
      let cmp = 0;
      if (typeof av === 'number' && typeof bv === 'number') {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return sort.dir === 'asc' ? cmp : -cmp;
    });
    return arr;
  }, [rows, sort, columns]);

  function onHeaderClick(col: Column<T>) {
    if (col.sortable === false) return;
    setSort((prev) => {
      if (!prev || prev.key !== col.key) {
        // First click: numeric cols default desc, text cols default asc
        const sample = rows[0] ? col.sortValue(rows[0]) : 0;
        const dir: 'asc' | 'desc' = typeof sample === 'number' ? 'desc' : 'asc';
        return { key: col.key, dir };
      }
      return { key: col.key, dir: prev.dir === 'asc' ? 'desc' : 'asc' };
    });
  }

  if (rows.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {columns.map((col) => {
              const isSorted = sort?.key === col.key;
              const arrow = !isSorted ? '' : sort.dir === 'asc' ? ' ↑' : ' ↓';
              const sortable = col.sortable !== false;
              return (
                <th
                  key={col.key}
                  title={col.tooltip}
                  onClick={() => onHeaderClick(col)}
                  style={{
                    padding: '12px 14px',
                    textAlign: col.align,
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: isSorted ? t.text : t.text3,
                    background: t.surface,
                    borderBottom: `1px solid ${t.border}`,
                    whiteSpace: 'nowrap',
                    cursor: sortable ? 'pointer' : 'default',
                    userSelect: 'none',
                  }}
                >
                  {col.label}
                  {arrow}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => {
            const key = getRowKey(row);
            const isHover = hovered === key;
            return (
              <tr
                key={key}
                onMouseEnter={() => setHovered(key)}
                onMouseLeave={() => setHovered(null)}
                style={{
                  borderTop: `1px solid ${t.border}`,
                  background: isHover ? t.surface : 'transparent',
                  transition: 'background 80ms ease',
                }}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    style={{
                      padding: '12px 14px',
                      textAlign: col.align,
                      fontFamily: col.align === 'right' ? FONT_MONO : undefined,
                    }}
                  >
                    {col.cell(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Lifecycle distribution chips — sits between panel header and table.
// ──────────────────────────────────────────────────────────────────────────
const LIFECYCLE_ORDER: LifecycleTagType[] = ['INITIAL', 'CONFIRMED', 'LATE', 'UNKNOWN'];

export function LifecycleChips({ rows }: { rows: ResearchRow[] }) {
  const { t } = useTheme();
  const counts = LIFECYCLE_ORDER.reduce<Record<LifecycleTagType, number>>(
    (acc, tag) => {
      acc[tag] = rows.filter((r) => r.lifecycle === tag).length;
      return acc;
    },
    { INITIAL: 0, CONFIRMED: 0, LATE: 0, UNKNOWN: 0 },
  );
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 8,
        padding: '12px 24px',
        borderBottom: `1px solid ${t.border}`,
        background: t.surface,
      }}
    >
      {LIFECYCLE_ORDER.map((tag) => (
        <span
          key={tag}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '4px 10px',
            background: t.bg,
            border: `1px solid ${t.border}`,
            borderRadius: 999,
            fontSize: 11,
            fontFamily: FONT_MONO,
            color: t.text3,
          }}
        >
          <LifecycleTag tag={tag} />
          <span style={{ color: t.text, fontWeight: 600 }}>{counts[tag]}</span>
        </span>
      ))}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Cell helpers — keep formatting consistent across panels.
// ──────────────────────────────────────────────────────────────────────────
export function PercentCell({
  value,
  decimals = 2,
  toneAt = 0,
}: {
  value: number;
  decimals?: number;
  toneAt?: number;
}) {
  const { t } = useTheme();
  const pct = value * 100;
  const color = pct > toneAt ? t.bullish : pct < -toneAt ? t.bearish : t.text2;
  const sign = pct >= 0 ? '+' : '';
  return (
    <span style={{ color, fontWeight: 600 }}>
      {sign}
      {pct.toFixed(decimals)}%
    </span>
  );
}

/**
 * "Distance from 50DMA" visual bar — value rendered as a horizontal band
 * scaled to ±20%, centered on 0. Above-50DMA = green, below = red.
 */
export function Dist50DmaCell({ value }: { value: number }) {
  const { t } = useTheme();
  const pct = value * 100;
  const RANGE = 20; // ±20%
  const clamped = Math.max(-RANGE, Math.min(RANGE, pct));
  const widthPct = (Math.abs(clamped) / RANGE) * 50; // half-track width
  const isUp = pct >= 0;
  const color = isUp ? t.bullish : t.bearish;
  return (
    <div
      style={{
        display: 'inline-flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        gap: 4,
        minWidth: 90,
      }}
    >
      <span
        style={{
          color: t.text2,
          fontFamily: FONT_MONO,
          fontWeight: 500,
        }}
      >
        {pct >= 0 ? '+' : ''}
        {pct.toFixed(1)}%
      </span>
      <div
        style={{
          position: 'relative',
          width: 80,
          height: 4,
          background: t.surface,
          borderRadius: 2,
          overflow: 'hidden',
        }}
      >
        {/* center marker */}
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: 0,
            bottom: 0,
            width: 1,
            background: t.border,
          }}
        />
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: isUp ? '50%' : `${50 - widthPct}%`,
            width: `${widthPct}%`,
            background: color,
            opacity: 0.7,
          }}
        />
      </div>
    </div>
  );
}

/** "Closeness to 52WH" — 0% = at the high, -3.2% = 3.2% below. */
export function Dist52whCell({ value }: { value: number }) {
  const { t } = useTheme();
  const pct = value * 100;
  return (
    <span style={{ color: t.text, fontWeight: 600 }}>
      {pct.toFixed(2)}%
    </span>
  );
}
