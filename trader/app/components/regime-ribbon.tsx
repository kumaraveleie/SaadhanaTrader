'use client';

import { useTheme } from './theme';
import { regimeLabel } from '../lib/labels';
import type { Regime } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * Shared regime + Nifty pill — top of /markets and / (home).
 *
 * Renders the dot-coloured regime label and today's Nifty change. The
 * optional ``footer`` slot below the pill takes the page-specific
 * second line: an interactive ``SectorStrip`` on /markets or a plain
 * "Strongest today: A · B · C" line on home.
 */
export function RegimeRibbon({
  regime,
  niftyPctChange,
  tooltip,
  footer,
}: {
  regime: Regime;
  niftyPctChange: number;
  tooltip?: string;
  footer?: React.ReactNode;
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

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        padding: '12px 16px',
        background: t.card,
        border: `1px solid ${t.border}`,
        borderRadius: 14,
        textAlign: 'left',
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
          title={tooltip}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            cursor: tooltip ? 'help' : 'default',
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
          <span
            style={{
              color: t.text,
              fontWeight: 600,
              textTransform: 'lowercase',
            }}
          >
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
      {footer}
    </div>
  );
}
