'use client';

import { useTheme } from '../components/theme';
import { FreshnessIndicator } from '../components/freshness-indicator';
import { SectorStrip } from '../components/sector-strip';
import { regimeLabel } from '../lib/labels';
import type { Regime, SectorStrength } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

export function ResearchHeader({
  scanDate,
  regime,
  universeSize,
  rowsScanned,
  niftyPctChange,
  sectors,
  selectedSector,
  onSelectSector,
}: {
  scanDate: string;
  regime: Regime;
  universeSize: number;
  rowsScanned: number;
  niftyPctChange: number;
  sectors: SectorStrength[];
  selectedSector: string | null;
  onSelectSector: (sector: string | null) => void;
}) {
  const { t } = useTheme();
  const niftyPct = niftyPctChange * 100;
  const niftyTone =
    niftyPct > 0 ? t.bullish : niftyPct < 0 ? t.bearish : t.text2;
  const label = regimeLabel(regime);
  const dotColor =
    label.tone === 'positive'
      ? t.bullish
      : label.tone === 'caution'
      ? t.bearish
      : t.text2;
  const ribbonTooltip =
    `${label.tooltip}\n\nScan covers ${rowsScanned} of ${universeSize} stocks today.`;

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
          maxWidth: 720,
          margin: '0 0 16px',
        }}
      >
        Stocks moving against the market — what&apos;s strong even when the
        index isn&apos;t.
      </p>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
          padding: '12px 16px',
          background: t.card,
          border: `1px solid ${t.border}`,
          borderRadius: 14,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            flexWrap: 'wrap',
            fontSize: 13,
            fontFamily: FONT_MONO,
            color: t.text2,
          }}
        >
          <span
            title={ribbonTooltip}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              cursor: 'help',
            }}
          >
            <span
              aria-hidden
              style={{
                width: 8,
                height: 8,
                borderRadius: 999,
                background: dotColor,
                display: 'inline-block',
              }}
            />
            <span style={{ color: t.text, fontWeight: 600, textTransform: 'lowercase' }}>
              {label.text}
            </span>
          </span>
          <span style={{ color: t.text3 }}>·</span>
          <span>
            Nifty{' '}
            <span style={{ color: niftyTone, fontWeight: 600 }}>
              {niftyPct >= 0 ? '+' : ''}
              {niftyPct.toFixed(2)}%
            </span>
          </span>
        </div>
        <SectorStrip
          sectors={sectors}
          selected={selectedSector}
          onSelect={onSelectSector}
        />
      </div>
    </header>
  );
}
