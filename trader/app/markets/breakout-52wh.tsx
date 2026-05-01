'use client';

import { useTheme } from '../components/theme';
import { LifecycleTag } from './lifecycle-tag';
import { PhaseTooltip } from '../components/phase-tooltip';
import { SymbolCell } from '../components/symbol-cell';
import {
  type Column,
  Dist52whCell,
  HelpIcon,
  LifecycleChips,
  PercentCell,
  SortableTable,
} from './research-table';
import type { ResearchRow } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export function Breakout52whPanel({
  rows,
  onPhaseHelp,
}: {
  rows: ResearchRow[];
  onPhaseHelp?: () => void;
}) {
  const { t } = useTheme();
  const columns = buildColumns({ onPhaseHelp });
  return (
    <section
      style={{
        border: `1px solid ${t.border}`,
        borderRadius: 16,
        background: t.card,
        overflow: 'hidden',
      }}
    >
      <header style={{ padding: '20px 24px', borderBottom: `1px solid ${t.border}` }}>
        <h2
          style={{
            fontSize: 18,
            fontWeight: 700,
            margin: 0,
            color: t.text,
            letterSpacing: '-0.02em',
          }}
        >
          52-Week High Breakout Watch
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
          Stocks within 5% of a fresh 52-week high with healthy momentum and
          institutional interest — top 20 by closeness to high.
        </p>
      </header>

      {rows.length === 0 ? (
        <Empty
          message="No symbols are currently within 5% of a 52-week high with the
          momentum + institutional-interest criteria — most names have pulled
          well below their highs."
        />
      ) : (
        <>
          <LifecycleChips rows={rows} onHelp={onPhaseHelp} />
          <SortableTable
            columns={columns}
            rows={rows}
            getRowKey={(r) => r.symbol}
          />
        </>
      )}
    </section>
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
      key: 'pct_change_5d',
      label: '5D %',
      tooltip: '5-trading-day return.',
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
      tooltip: '14-period RSI. 50–75 here = healthy, not yet overbought.',
      align: 'right',
      sortValue: (r) => r.rsi_14,
      cell: (r) => <DimNumber value={r.rsi_14.toFixed(0)} />,
    },
    {
      key: 'pro_setup_score',
      label: 'Score',
      tooltip:
        'Pro-Setup Score — how many of the 13 entry conditions are firing. 13/13 = full match.',
      align: 'right',
      sortValue: (r) => r.pro_setup_score,
      cell: (r) => <ScoreCell value={r.pro_setup_score} />,
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
  return <span style={{ color: t.text2, fontSize: 12 }}>{value}</span>;
}

function DimNumber({ value }: { value: string }) {
  const { t } = useTheme();
  return <span style={{ color: t.text2 }}>{value}</span>;
}

function ScoreCell({ value }: { value: number }) {
  const { t } = useTheme();
  const color = value >= 11 ? t.bullish : t.text2;
  return (
    <span style={{ color, fontWeight: 600 }}>
      {value}/13
    </span>
  );
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

function Empty({ message }: { message: string }) {
  const { t } = useTheme();
  return (
    <div style={{ padding: '36px 24px', textAlign: 'center' }}>
      <p
        style={{
          fontSize: 14,
          color: t.text2,
          margin: 0,
          lineHeight: 1.6,
          maxWidth: 560,
          marginInline: 'auto',
        }}
      >
        {message}
      </p>
    </div>
  );
}
