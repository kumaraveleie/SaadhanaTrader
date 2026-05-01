'use client';

import { useTheme } from '../../components/theme';
import {
  CATALYST_LABEL,
  CATALYST_TONE,
  FRESHNESS_LABEL,
} from '../../lib/labels';
import type { Catalyst, CatalystType, FreshnessTag } from '../../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * §13 Phase D catalyst card for /stock/[symbol]. Always rendered —
 * empty state when the symbol has no catalysts, full list otherwise.
 *
 * Catalysts and pattern-match are independent signal dimensions:
 * - A symbol can have catalysts without a pattern match (information
 *   only — not a trade signal)
 * - A symbol can match the pattern without catalysts (pure-technical
 *   signal — flagged as suspicious if RVOL is high but no catalyst)
 */
export function CatalystSection({
  catalysts,
  highConviction,
}: {
  catalysts: Catalyst[];
  highConviction: boolean;
}) {
  const count = catalysts.length;

  if (count === 0) {
    return (
      <Card title="Catalysts">
        <Empty />
      </Card>
    );
  }

  // Sort FRESH → RECENT → STALE, then date desc within each bucket
  const order = { FRESH: 0, RECENT: 1, STALE: 2 } as const;
  const sorted = [...catalysts].sort((a, b) => {
    const cmp = order[a.freshness] - order[b.freshness];
    if (cmp !== 0) return cmp;
    return a.date < b.date ? 1 : -1;
  });

  return (
    <Card
      title={`Catalysts (${count} active)`}
      subtitle="Why institutions are paying attention to this stock"
      highConviction={highConviction}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {sorted.map((c, i) => (
          <CatalystRow key={`${c.type}-${c.date}-${i}`} catalyst={c} />
        ))}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Card shell
// ──────────────────────────────────────────────────────────────────────
function Card({
  title,
  subtitle,
  highConviction,
  children,
}: {
  title: string;
  subtitle?: string;
  highConviction?: boolean;
  children: React.ReactNode;
}) {
  const { t } = useTheme();
  return (
    <section
      style={{
        border: `1px solid ${highConviction ? t.bullish : t.border}`,
        borderRadius: 14,
        background: t.card,
        overflow: 'hidden',
      }}
    >
      <header
        style={{
          padding: '16px 22px',
          borderBottom: `1px solid ${t.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          flexWrap: 'wrap',
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
            {title}
          </h2>
          {subtitle && (
            <p
              style={{
                fontSize: 12,
                color: t.text3,
                margin: '4px 0 0',
                fontFamily: FONT_MONO,
              }}
            >
              {subtitle}
            </p>
          )}
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
      </header>
      <div style={{ padding: '20px 22px' }}>{children}</div>
    </section>
  );
}

function Empty() {
  const { t } = useTheme();
  return (
    <p
      style={{
        fontSize: 14,
        color: t.text2,
        margin: 0,
        lineHeight: 1.6,
        maxWidth: 560,
      }}
    >
      No active catalysts in the last 90 days. The system surfaces
      catalysts when corporate filings, institutional flows, or sector
      momentum suggest something is happening.
    </p>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Per-catalyst row
// ──────────────────────────────────────────────────────────────────────
const HIGH_CONVICTION_MAGNITUDE = 7;
const DETAIL_TRUNCATE = 90;

function CatalystRow({ catalyst }: { catalyst: Catalyst }) {
  const { t } = useTheme();
  const tone = CATALYST_TONE[catalyst.type];
  const toneColor =
    tone === 'positive' ? t.bullish : tone === 'caution' ? t.bearish : t.text2;
  const truncated =
    catalyst.detail.length > DETAIL_TRUNCATE
      ? catalyst.detail.slice(0, DETAIL_TRUNCATE).trimEnd() + '…'
      : catalyst.detail;
  const isHigh = catalyst.magnitude_score >= HIGH_CONVICTION_MAGNITUDE;
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
        padding: '10px 12px',
        background: t.surface,
        border: `1px solid ${t.border}`,
        borderRadius: 8,
      }}
    >
      <CategoryIcon type={catalyst.type} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexWrap: 'wrap',
            marginBottom: 4,
          }}
        >
          <span style={{ color: toneColor, fontWeight: 600, fontSize: 13 }}>
            {CATALYST_LABEL[catalyst.type]}
          </span>
          <FreshnessPill freshness={catalyst.freshness} />
          {isHigh && <MagnitudeBadge magnitude={catalyst.magnitude_score} />}
          <span
            style={{
              fontSize: 11,
              color: t.text3,
              fontFamily: FONT_MONO,
            }}
          >
            {catalyst.days_old}d ago
          </span>
        </div>
        <div style={{ fontSize: 13, color: t.text2, lineHeight: 1.5 }}>
          {truncated}
        </div>
      </div>
      {catalyst.source_url && (
        <a
          href={catalyst.source_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: t.text3,
            fontSize: 14,
            textDecoration: 'none',
            paddingLeft: 4,
          }}
          title="View source filing"
        >
          ↗
        </a>
      )}
    </div>
  );
}

// Per user's spec: 🟢 buying / 🔵 corporate action / 🟡 caution sells / ⚪ unknown
function CategoryIcon({ type }: { type: CatalystType }) {
  const { t } = useTheme();
  const icon = ICON_FOR_TYPE[type] ?? '⚪';
  return (
    <span
      aria-hidden
      style={{
        fontSize: 18,
        lineHeight: 1,
        marginTop: 1,
      }}
    >
      {icon}
    </span>
  );
}

const ICON_FOR_TYPE: Record<CatalystType, string> = {
  // Buying
  fii_increase: '🟢',
  dii_increase: '🟢',
  promoter_buying: '🟢',
  insider_buying: '🟢',
  block_deal_buy: '🟢',
  // Corporate action
  earnings_beat: '🔵',
  guidance_raise: '🔵',
  buyback: '🔵',
  m_and_a: '🔵',
  policy_tailwind: '🔵',
  sector_momentum: '🔵',
  // Caution / sells
  promoter_selling: '🟡',
  block_deal_sell: '🟡',
  // Mgmt change is informational; lean neutral.
  management_change: '⚪',
};

function FreshnessPill({ freshness }: { freshness: FreshnessTag }) {
  const { t } = useTheme();
  const fg =
    freshness === 'FRESH' ? t.bullish : freshness === 'RECENT' ? t.text2 : t.text3;
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

function MagnitudeBadge({ magnitude }: { magnitude: number }) {
  const { t } = useTheme();
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '1px 6px',
        background: 'rgba(0,255,136,0.12)',
        color: t.bullish,
        border: `1px solid ${t.bullish}`,
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        fontFamily: FONT_MONO,
      }}
      title="High-conviction catalyst (magnitude ≥ 7)"
    >
      HIGH · {magnitude}/10
    </span>
  );
}
