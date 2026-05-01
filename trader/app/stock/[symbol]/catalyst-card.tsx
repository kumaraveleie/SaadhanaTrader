'use client';

import { useTheme } from '../../components/theme';
import { CatalystChip } from '../../components/catalyst-chip';
import type { Catalyst } from '../../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * §13 Phase D catalyst card for the /stock/[symbol] page. Renders the
 * full list of catalysts attached to this symbol, sorted by freshness
 * (FRESH first, then by date desc within each bucket). Hidden entirely
 * when no catalysts are present — caller decides empty-state copy.
 */
export function CatalystCard({
  catalysts,
  highConviction,
}: {
  catalysts: Catalyst[];
  highConviction?: boolean;
}) {
  const { t } = useTheme();
  if (catalysts.length === 0) return null;

  const order = { FRESH: 0, RECENT: 1, STALE: 2 } as const;
  const sorted = [...catalysts].sort((a, b) => {
    const cmp = order[a.freshness] - order[b.freshness];
    if (cmp !== 0) return cmp;
    // Within bucket, most recent first
    return a.date < b.date ? 1 : -1;
  });

  return (
    <section
      style={{
        border: `1px solid ${highConviction ? t.bullish : t.border}`,
        borderRadius: 14,
        background: t.card,
        padding: '20px 22px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 14,
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div>
          <h2
            style={{
              fontSize: 16,
              fontWeight: 700,
              margin: 0,
              color: t.text,
              letterSpacing: '-0.02em',
            }}
          >
            Catalysts
          </h2>
          <p
            style={{
              fontSize: 12,
              color: t.text3,
              margin: '4px 0 0',
              fontFamily: FONT_MONO,
            }}
          >
            {catalysts.length} event{catalysts.length === 1 ? '' : 's'} from
            corporate filings
          </p>
        </div>
        {highConviction && (
          <span
            style={{
              fontSize: 11,
              fontFamily: FONT_MONO,
              color: t.bullish,
              fontWeight: 600,
              padding: '3px 8px',
              border: `1px solid ${t.bullish}`,
              borderRadius: 4,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
            }}
          >
            High conviction
          </span>
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {sorted.map((c, i) => (
          <CatalystChip key={`${c.type}-${c.date}-${i}`} catalyst={c} />
        ))}
      </div>
    </section>
  );
}
