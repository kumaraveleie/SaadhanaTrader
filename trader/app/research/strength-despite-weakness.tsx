'use client';

import Link from 'next/link';
import { useTheme } from '../components/theme';
import { LifecycleTag } from './lifecycle-tag';
import type { ResearchRow } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export function StrengthDespiteWeaknessPanel({
  rows,
  niftyPctChange,
}: {
  rows: ResearchRow[];
  niftyPctChange: number;
}) {
  const { t } = useTheme();
  const niftyPct = (niftyPctChange * 100).toFixed(2);
  return (
    <PanelShell
      title="Strength Despite Weakness"
      subtitle={
        <>
          Stocks making new highs while broader market falls. Lifecycle tag
          indicates where in the move the stock currently sits. <strong style={{ color: t.text2 }}>Research only —
          Saadhana §12 trading rule still applies.</strong> INITIAL = fresh strength,
          CONFIRMED = trend running, LATE = limited upside, do not chase.
        </>
      }
    >
      {niftyPctChange >= 0 ? (
        <Empty
          message={
            <>
              Nifty closed up <strong style={{ color: t.text }}>{niftyPct}%</strong> today.
              This panel surfaces divergent strength only when the broader
              market is falling — by definition there is none today.
            </>
          }
        />
      ) : rows.length === 0 ? (
        <Empty
          message={
            <>
              Nifty closed <strong style={{ color: t.text }}>{niftyPct}%</strong> today,
              but no Tier-1-passing industrial name closed up AND within 5%
              of its 52-week high. Divergent strength is rare; today it isn&apos;t
              showing.
            </>
          }
        />
      ) : (
        <Table rows={rows} />
      )}
    </PanelShell>
  );
}

function Table({ rows }: { rows: ResearchRow[] }) {
  const { t } = useTheme();
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {[
              { label: 'Symbol', align: 'left' as const },
              { label: 'Sector', align: 'left' as const },
              { label: 'Today %', align: 'right' as const },
              { label: 'Dist 52WH', align: 'right' as const },
              { label: 'Lifecycle', align: 'left' as const },
              { label: 'RSI', align: 'right' as const },
              { label: 'Dist 50DMA', align: 'right' as const },
              { label: 'Inst flow 30b', align: 'right' as const },
            ].map((h) => (
              <th
                key={h.label}
                style={{
                  padding: '12px 14px',
                  textAlign: h.align,
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: t.text3,
                  background: t.surface,
                  borderBottom: `1px solid ${t.border}`,
                  whiteSpace: 'nowrap',
                }}
              >
                {h.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <Row key={r.symbol} row={r} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Row({ row }: { row: ResearchRow }) {
  const { t } = useTheme();
  const todayColor =
    row.pct_change_today > 0.02
      ? t.bullish
      : row.pct_change_today > 0
      ? t.text
      : t.text2;
  return (
    <tr style={{ borderTop: `1px solid ${t.border}` }}>
      <td style={{ padding: '12px 14px' }}>
        <Link
          href={`/stock/${encodeURIComponent(row.symbol)}`}
          style={{ color: t.text, fontWeight: 600, fontFamily: FONT_MONO }}
        >
          {row.symbol}
        </Link>
      </td>
      <td style={{ padding: '12px 14px', color: t.text3, fontSize: 12 }}>
        {row.sector}
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: FONT_MONO, color: todayColor, fontWeight: 600 }}>
        {(row.pct_change_today * 100).toFixed(2)}%
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: FONT_MONO, color: t.text2 }}>
        {(row.dist_from_52wh_pct * 100).toFixed(2)}%
      </td>
      <td style={{ padding: '12px 14px' }}>
        <LifecycleTag tag={row.lifecycle} />
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: FONT_MONO, color: t.text2 }}>
        {row.rsi_14.toFixed(0)}
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: FONT_MONO, color: t.text2 }}>
        {(row.dist_from_50dma_pct * 100).toFixed(1)}%
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: FONT_MONO, color: row.inst_flow_score_30b > 0 ? t.bullish : t.text2 }}>
        {row.inst_flow_score_30b > 0 ? '+' : ''}{row.inst_flow_score_30b}
      </td>
    </tr>
  );
}

function PanelShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: React.ReactNode;
  children: React.ReactNode;
}) {
  const { t } = useTheme();
  return (
    <section
      style={{
        border: `1px solid ${t.border}`,
        borderRadius: 16,
        background: t.card,
        overflow: 'hidden',
      }}
    >
      <header
        style={{
          padding: '20px 24px',
          borderBottom: `1px solid ${t.border}`,
        }}
      >
        <h2
          style={{
            fontSize: 18,
            fontWeight: 700,
            margin: 0,
            color: t.text,
            letterSpacing: '-0.02em',
          }}
        >
          {title}
        </h2>
        <p
          style={{
            fontSize: 13,
            color: t.text3,
            margin: '6px 0 0',
            lineHeight: 1.55,
            maxWidth: 800,
          }}
        >
          {subtitle}
        </p>
      </header>
      {children}
    </section>
  );
}

function Empty({ message }: { message: React.ReactNode }) {
  const { t } = useTheme();
  return (
    <div style={{ padding: '36px 24px', textAlign: 'center' }}>
      <p style={{ fontSize: 14, color: t.text2, margin: 0, lineHeight: 1.65, maxWidth: 560, marginInline: 'auto' }}>
        {message}
      </p>
    </div>
  );
}
