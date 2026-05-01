'use client';

import { useTheme } from './theme';
import { CATALYST_TONE, FRESHNESS_LABEL, catalystLabel } from '../lib/labels';
import type { Catalyst, FreshnessTag } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';
const DETAIL_TRUNCATE = 60;

/**
 * §13 Phase D catalyst chip. Renders a single catalyst as:
 *   [type badge] [freshness pill] short detail (truncated) [↗ source link]
 *
 * Used in three places:
 *  - /research sector drill-down "Triggers" highlights
 *  - /stock/[symbol] catalyst card list
 *  - /scanner stock-card chip count tooltip (count-only variant)
 */
export function CatalystChip({
  catalyst,
  showSymbol,
}: {
  catalyst: Catalyst & { symbol?: string };
  showSymbol?: boolean;
}) {
  const { t } = useTheme();
  const tone = CATALYST_TONE[catalyst.type];
  const toneColor =
    tone === 'positive'
      ? t.bullish
      : tone === 'caution'
      ? t.bearish
      : t.text2;
  const truncated =
    catalyst.detail.length > DETAIL_TRUNCATE
      ? catalyst.detail.slice(0, DETAIL_TRUNCATE).trimEnd() + '…'
      : catalyst.detail;
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 10px',
        background: t.surface,
        border: `1px solid ${t.border}`,
        borderRadius: 8,
        fontSize: 12,
        flexWrap: 'wrap',
      }}
    >
      {showSymbol && catalyst.symbol && (
        <span
          style={{
            fontFamily: FONT_MONO,
            color: t.text,
            fontWeight: 600,
            paddingRight: 4,
            borderRight: `1px solid ${t.border}`,
          }}
        >
          {catalyst.symbol}
        </span>
      )}
      <span
        style={{
          color: toneColor,
          fontWeight: 600,
          fontSize: 11,
        }}
      >
        {catalystLabel(catalyst.type)}
      </span>
      <FreshnessPill freshness={catalyst.freshness} />
      <span style={{ color: t.text2, fontSize: 12, lineHeight: 1.4 }}>
        {truncated}
      </span>
      {catalyst.source_url && (
        <a
          href={catalyst.source_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: t.text3,
            fontSize: 11,
            textDecoration: 'none',
            marginLeft: 'auto',
            paddingLeft: 6,
          }}
          title="View source filing"
        >
          ↗
        </a>
      )}
    </div>
  );
}

/** Compact chip-count badge for /scanner stock cards. */
export function CatalystChipCount({
  freshCount,
  recentCount,
  highConviction,
}: {
  freshCount: number;
  recentCount: number;
  highConviction: boolean;
}) {
  const { t } = useTheme();
  const total = freshCount + recentCount;
  if (total === 0) return null;
  const labelParts: string[] = [];
  if (freshCount > 0) labelParts.push(`${freshCount} fresh`);
  if (recentCount > 0) labelParts.push(`${recentCount} recent`);
  return (
    <span
      title={
        highConviction
          ? 'Includes high-conviction catalyst (FRESH + magnitude ≥ 7)'
          : 'Tap stock to view catalyst details'
      }
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        background: highConviction ? 'rgba(0,255,136,0.15)' : t.surface,
        border: `1px solid ${highConviction ? t.bullish : t.border}`,
        borderRadius: 999,
        fontSize: 11,
        fontFamily: FONT_MONO,
        color: highConviction ? t.bullish : t.text2,
        fontWeight: 600,
      }}
    >
      <span>●</span>
      <span>{labelParts.join(' · ')}</span>
    </span>
  );
}

function FreshnessPill({ freshness }: { freshness: FreshnessTag }) {
  const { t } = useTheme();
  const fg =
    freshness === 'FRESH'
      ? t.bullish
      : freshness === 'RECENT'
      ? t.text2
      : t.text3;
  const bg =
    freshness === 'FRESH'
      ? 'rgba(0,255,136,0.12)'
      : freshness === 'RECENT'
      ? 'rgba(255,255,255,0.04)'
      : 'transparent';
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '1px 6px',
        background: bg,
        color: fg,
        border: `1px solid ${freshness === 'FRESH' ? t.bullish : t.border}`,
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
      }}
    >
      {FRESHNESS_LABEL[freshness]}
    </span>
  );
}
