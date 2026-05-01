'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useTheme } from '../components/theme';
import { CatalystChipCount } from '../components/catalyst-chip';
import { SignalPill } from '../components/signal-pill';
import type { CandidateRow } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

type SortKey = 'symbol' | 'pro_setup_score' | 'drs';
type SortDir = 'asc' | 'desc';

export function ScannerTable({ candidates }: { candidates: CandidateRow[] }) {
  const { t } = useTheme();
  const [sortKey, setSortKey] = useState<SortKey>('pro_setup_score');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const sorted = [...candidates].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (typeof av === 'string' && typeof bv === 'string') {
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    const an = typeof av === 'number' ? av : 0;
    const bn = typeof bv === 'number' ? bv : 0;
    return sortDir === 'asc' ? an - bn : bn - an;
  });

  const onHeader = (key: SortKey) => () => {
    if (key === sortKey) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir(key === 'symbol' ? 'asc' : 'desc');
    }
  };

  return (
    <div
      style={{
        borderRadius: 12,
        border: `1px solid ${t.border}`,
        background: t.card,
        overflow: 'hidden',
      }}
    >
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: 14,
          color: t.text,
        }}
      >
        <thead>
          <tr>
            <Th onClick={onHeader('symbol')} active={sortKey === 'symbol'} dir={sortDir} t={t}>
              Symbol
            </Th>
            <Th t={t}>Status</Th>
            <Th
              onClick={onHeader('pro_setup_score')}
              active={sortKey === 'pro_setup_score'}
              dir={sortDir}
              align="right"
              t={t}
            >
              Score
            </Th>
            <Th
              onClick={onHeader('drs')}
              active={sortKey === 'drs'}
              dir={sortDir}
              align="right"
              t={t}
            >
              Drawdown Resistance
            </Th>
            <Th align="right" t={t}>
              Entry
            </Th>
            <Th align="right" t={t}>
              Stop
            </Th>
            <Th align="right" t={t}>
              T1
            </Th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => (
            <tr
              key={c.symbol}
              style={{
                borderTop: `1px solid ${t.border}`,
                cursor: 'pointer',
              }}
            >
              <td style={{ padding: '14px 16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <Link
                    href={`/stock/${encodeURIComponent(c.symbol)}`}
                    style={{
                      color: t.text,
                      fontWeight: 600,
                      fontFamily: FONT_MONO,
                      letterSpacing: '0.02em',
                    }}
                  >
                    {c.symbol}
                  </Link>
                  <CatalystChipCount
                    freshCount={c.catalyst_count_fresh ?? 0}
                    recentCount={c.catalyst_count_recent ?? 0}
                    highConviction={c.has_high_conviction_catalyst ?? false}
                  />
                </div>
              </td>
              <td style={{ padding: '14px 16px' }}>
                <SignalPill signal={c.signal} />
              </td>
              <td
                style={{
                  padding: '14px 16px',
                  textAlign: 'right',
                  fontFamily: FONT_MONO,
                  color: c.pro_setup_score === 13 ? t.bullish : t.text2,
                }}
              >
                {c.pro_setup_score}/13
              </td>
              <td
                style={{
                  padding: '14px 16px',
                  textAlign: 'right',
                  fontFamily: FONT_MONO,
                  color: t.text2,
                }}
              >
                {c.drs?.toFixed?.(0) ?? '—'}
              </td>
              <td style={{ padding: '14px 16px', textAlign: 'right', fontFamily: FONT_MONO, color: t.text2 }}>
                {c.entry_price !== undefined ? `₹${c.entry_price.toFixed(2)}` : '—'}
              </td>
              <td style={{ padding: '14px 16px', textAlign: 'right', fontFamily: FONT_MONO, color: t.text2 }}>
                {c.stop_loss !== undefined ? `₹${c.stop_loss.toFixed(2)}` : '—'}
              </td>
              <td style={{ padding: '14px 16px', textAlign: 'right', fontFamily: FONT_MONO, color: t.text2 }}>
                {c.target_t1 !== undefined ? `₹${c.target_t1.toFixed(2)}` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Th({
  children,
  onClick,
  active,
  dir,
  align,
  t,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  active?: boolean;
  dir?: SortDir;
  align?: 'left' | 'right';
  t: ReturnType<typeof useTheme>['t'];
}) {
  const arrow = active ? (dir === 'asc' ? ' ↑' : ' ↓') : '';
  return (
    <th
      onClick={onClick}
      style={{
        padding: '14px 16px',
        textAlign: align ?? 'left',
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        color: t.text3,
        cursor: onClick ? 'pointer' : 'default',
        userSelect: 'none',
        background: t.surface,
        borderBottom: `1px solid ${t.border}`,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
      {arrow}
    </th>
  );
}
