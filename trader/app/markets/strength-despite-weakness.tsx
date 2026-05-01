'use client';

import { useTheme } from '../components/theme';
import { LifecycleTag } from './lifecycle-tag';
import { PhaseTooltip } from '../components/phase-tooltip';
import { SymbolCell } from '../components/symbol-cell';
import {
  type Column,
  Dist50DmaCell,
  Dist52whCell,
  HelpIcon,
  LifecycleChips,
  PercentCell,
  SortableTable,
} from './research-table';
import type { ResearchRow } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export function StrengthDespiteWeaknessPanel({
  rows,
  niftyPctChange,
  onPhaseHelp,
}: {
  rows: ResearchRow[];
  niftyPctChange: number;
  onPhaseHelp?: () => void;
}) {
  const { t } = useTheme();
  const niftyPct = (niftyPctChange * 100).toFixed(2);
  const initialCount = rows.filter((r) => r.lifecycle === 'INITIAL').length;
  const columns = buildColumns({ onPhaseHelp });

  return (
    <PanelShell
      title="Strength Despite Weakness"
      subtitle="Stocks up while the market falls — closer to a fresh high = stronger."
    >
      {niftyPctChange >= 0 ? (
        <Empty
          message={
            <>
              Nifty closed up <strong style={{ color: t.text }}>+{niftyPct}%</strong>{' '}
              today. This panel only shows divergent strength on red-market days
              — there&apos;s nothing to surface here today.
            </>
          }
        />
      ) : rows.length === 0 ? (
        <Empty
          message={
            <>
              Nifty closed <strong style={{ color: t.text }}>{niftyPct}%</strong>,
              but no stock that passes our quality filter closed up AND within 5%
              of its 52-week high. Divergent strength is rare; today it isn&apos;t
              showing.
            </>
          }
        />
      ) : (
        <>
          <LifecycleChips rows={rows} onHelp={onPhaseHelp} />
          {initialCount === 0 && (
            <InitialNote
              note={`No Breakout setups today — all ${rows.length} divergent names
              are already mid-trend or late.`}
            />
          )}
          <SortableTable
            columns={columns}
            rows={rows}
            getRowKey={(r) => r.symbol}
          />
        </>
      )}
    </PanelShell>
  );
}

function buildColumns({
  onPhaseHelp,
}: {
  onPhaseHelp?: () => void;
}): Column<ResearchRow>[] {
  return [
    {
      key: 'symbol',
      label: 'Symbol',
      align: 'left',
      sortValue: (r) => r.symbol,
      cell: (r) => <SymbolCell symbol={r.symbol} />,
    },
    {
      key: 'sub_industry',
      label: 'Sub-sector',
      tooltip: 'NSE Industry — finer-grained than the broad sector bucket.',
      align: 'left',
      sortValue: (r) => r.sub_industry,
      cell: (r) => <SubsectorCell value={r.sub_industry} />,
    },
    {
      key: 'pct_change_today',
      label: 'Today %',
      tooltip: "Today's close vs yesterday's close.",
      align: 'right',
      sortValue: (r) => r.pct_change_today,
      cell: (r) => <PercentCell value={r.pct_change_today} />,
    },
    {
      key: 'pct_change_5d',
      label: '5D %',
      tooltip: '5-trading-day return — confirms whether today is part of a real run.',
      align: 'right',
      sortValue: (r) => r.pct_change_5d,
      cell: (r) => <PercentCell value={r.pct_change_5d} />,
    },
    {
      key: 'dist_from_52wh_pct',
      label: 'Close to 52WH',
      tooltip: 'How close the stock is to its 52-week high. 0% = at the high.',
      align: 'right',
      sortValue: (r) => r.dist_from_52wh_pct,
      cell: (r) => <Dist52whCell value={r.dist_from_52wh_pct} />,
    },
    {
      key: 'phase',
      label: 'Phase',
      tooltip: 'Where in the move this stock sits — Breakout fresh, Extended limited.',
      align: 'left',
      sortValue: (r) =>
        ({ INITIAL: 0, CONFIRMED: 1, LATE: 2, UNKNOWN: 3 }[r.lifecycle]),
      cell: (r) => (
        <PhaseTooltip tag={r.lifecycle} onLearnMore={onPhaseHelp}>
          <LifecycleTag tag={r.lifecycle} />
        </PhaseTooltip>
      ),
      labelAdornment: onPhaseHelp ? (
        <HelpIcon label="How to read phases" onClick={onPhaseHelp} />
      ) : undefined,
    },
    {
      key: 'rsi_14',
      label: 'RSI',
      tooltip: '14-period RSI. >70 = stretched, 50–70 = healthy momentum.',
      align: 'right',
      sortValue: (r) => r.rsi_14,
      cell: (r) => <DimNumber value={r.rsi_14.toFixed(0)} />,
    },
    {
      key: 'dist_from_50dma_pct',
      label: 'Vs 50DMA',
      tooltip: 'Distance from 50-day moving average. Bar shows position vs ±20%.',
      align: 'right',
      sortValue: (r) => r.dist_from_50dma_pct,
      cell: (r) => <Dist50DmaCell value={r.dist_from_50dma_pct} />,
    },
    {
      key: 'rvol_today',
      label: 'Volume',
      tooltip: "Today's volume vs the 50-day average. >1.5× = unusual interest.",
      align: 'right',
      sortValue: (r) => r.rvol_today,
      cell: (r) => <RvolCell value={r.rvol_today} />,
    },
  ];
}

function SubsectorCell({ value }: { value: string }) {
  const { t } = useTheme();
  return (
    <span style={{ color: t.text2, fontSize: 12 }}>{value}</span>
  );
}

function DimNumber({ value }: { value: string }) {
  const { t } = useTheme();
  return <span style={{ color: t.text2 }}>{value}</span>;
}

function RvolCell({ value }: { value: number }) {
  const { t } = useTheme();
  const isHigh = value >= 1.5;
  const color = isHigh ? t.bullish : value < 0.7 ? t.text3 : t.text2;
  return (
    <span style={{ color, fontWeight: isHigh ? 600 : 500 }}>
      {value.toFixed(2)}×
    </span>
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
      <p
        style={{
          fontSize: 14,
          color: t.text2,
          margin: 0,
          lineHeight: 1.65,
          maxWidth: 560,
          marginInline: 'auto',
        }}
      >
        {message}
      </p>
    </div>
  );
}

function InitialNote({ note }: { note: string }) {
  const { t } = useTheme();
  return (
    <div
      style={{
        padding: '10px 24px',
        borderBottom: `1px solid ${t.border}`,
        background: t.bg,
        fontSize: 12,
        color: t.text3,
        lineHeight: 1.5,
      }}
    >
      {note}
    </div>
  );
}
