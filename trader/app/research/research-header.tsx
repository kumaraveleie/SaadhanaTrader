'use client';

import { useTheme } from '../components/theme';
import { FreshnessIndicator } from '../components/freshness-indicator';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export function ResearchHeader({
  scanDate,
  universeSize,
  rowsScanned,
  niftyPctChange,
}: {
  scanDate: string;
  universeSize: number;
  rowsScanned: number;
  niftyPctChange: number;
}) {
  const { t } = useTheme();
  const niftyPct = niftyPctChange * 100;
  const niftyTone =
    niftyPct > 0 ? t.bullish : niftyPct < 0 ? t.bearish : t.text2;
  return (
    <header>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 16,
          marginBottom: 12,
        }}
      >
        <h1
          style={{
            fontSize: 'clamp(28px, 4vw, 36px)',
            fontWeight: 700,
            letterSpacing: '-0.03em',
            margin: 0,
            color: t.text,
          }}
        >
          Research
        </h1>
        <FreshnessIndicator scanDate={scanDate} />
      </div>

      <p
        style={{
          fontSize: 14,
          color: t.text2,
          lineHeight: 1.6,
          maxWidth: 800,
          margin: '0 0 20px',
        }}
      >
        Universe-wide context that the §5 BUY scanner doesn&apos;t surface
        — sector strength, divergent strength, breakout proximity. <strong style={{ color: t.text2 }}>
        Visible in all regimes including Risk-Off.</strong> No BUY action enabled here;
        the §12 trading rule still applies. This page is research, not a trade signal.
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: 12,
        }}
      >
        <Stat
          label="Nifty 50 today"
          value={`${niftyPct >= 0 ? '+' : ''}${niftyPct.toFixed(2)}%`}
          valueColor={niftyTone}
        />
        <Stat label="Universe" value={`${universeSize} symbols`} />
        <Stat label="Rows scanned" value={`${rowsScanned}`} />
      </div>
    </header>
  );
}

function Stat({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  const { t } = useTheme();
  return (
    <div
      style={{
        padding: '14px 18px',
        background: t.card,
        border: `1px solid ${t.border}`,
        borderRadius: 12,
      }}
    >
      <div
        style={{
          fontSize: 11,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: t.text3,
          fontFamily: FONT_MONO,
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 18, fontWeight: 600, color: valueColor ?? t.text }}>
        {value}
      </div>
    </div>
  );
}
