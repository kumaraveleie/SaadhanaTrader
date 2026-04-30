'use client';

import Link from 'next/link';
import { useTheme } from './theme';
import { LifecycleTag } from '../research/lifecycle-tag';
import { PhaseTooltip } from './phase-tooltip';
import type { SectorStrength } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * Inline drill-down panel for a clicked sector chip. Renders:
 *  - Triggers (Phase D placeholder copy)
 *  - Technical (RS over 5d/20d/60d, breadth)
 *  - Top stocks driving the move
 *  - Institutional footprint
 *  - Action: open scanner filtered to sector
 */
export function SectorDrill({
  sector,
  totalSectorCount,
  onClose,
  onPhaseLearnMore,
}: {
  sector: SectorStrength;
  totalSectorCount: number;
  onClose: () => void;
  onPhaseLearnMore?: () => void;
}) {
  const { t } = useTheme();
  const pct = sector.today_pct * 100;
  const tone = pct > 0 ? t.bullish : pct < 0 ? t.bearish : t.text2;

  return (
    <section
      role="region"
      aria-labelledby="sector-drill-title"
      style={{
        border: `1px solid ${t.border}`,
        borderRadius: 14,
        background: t.card,
        marginBottom: 24,
        overflow: 'hidden',
      }}
    >
      <header
        style={{
          padding: '18px 22px',
          borderBottom: `1px solid ${t.border}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 16,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <h3
            id="sector-drill-title"
            style={{
              fontSize: 18,
              fontWeight: 700,
              margin: 0,
              color: t.text,
              letterSpacing: '-0.02em',
            }}
          >
            {sector.sector_label}{' '}
            <span style={{ color: tone, fontFamily: FONT_MONO, fontSize: 16 }}>
              {pct >= 0 ? '+' : ''}
              {pct.toFixed(2)}%
            </span>
          </h3>
          <p style={{ fontSize: 12, color: t.text3, margin: '4px 0 0' }}>
            {sector.sector_count} stocks · rank #{sector.rank_by_inst_flow} of{' '}
            {totalSectorCount} by institutional flow today
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close sector drill"
          style={{
            background: 'transparent',
            border: 'none',
            color: t.text2,
            fontSize: 22,
            cursor: 'pointer',
            padding: 4,
            lineHeight: 1,
          }}
        >
          ×
        </button>
      </header>

      <div style={{ padding: '8px 0' }}>
        <Block title="Triggers" hint="Phase D pending">
          <p style={{ fontSize: 13, color: t.text3, lineHeight: 1.6, margin: 0 }}>
            Fundamental triggers, news catalysts, FII flow narrative, and
            management commentary will appear here once the catalyst engine
            ships in Phase D. Until then, see Technical and Top Stocks
            below for the deterministic signals.
          </p>
        </Block>

        <Block title="Technical">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 12,
            }}
          >
            <Stat
              label="Sector RS vs Nifty"
              value={
                <span style={{ fontFamily: FONT_MONO, color: t.text }}>
                  {fmtRs(sector.rs_5d)} <DimSlash /> {fmtRs(sector.rs_20d)}{' '}
                  <DimSlash /> {fmtRs(sector.rs_60d)}
                </span>
              }
              note="5d · 20d · 60d"
            />
            <Stat
              label="Breadth above 50-DMA"
              value={
                <BreadthBar value={sector.breadth_above_50dma} />
              }
            />
            <Stat
              label="Breadth above 200-DMA"
              value={
                <BreadthBar value={sector.breadth_above_200dma} />
              }
            />
          </div>
          <p style={{ fontSize: 12, color: t.text3, marginTop: 14 }}>
            Sector phase:{' '}
            <span style={{ color: t.text2, fontFamily: FONT_MONO, fontWeight: 600 }}>
              {sector.sector_phase}
            </span>{' '}
            <span style={{ color: t.text3, fontStyle: 'italic' }}>
              · {sector.sector_phase_note}
            </span>
          </p>
        </Block>

        <Block title="Top stocks driving the move">
          {sector.top_stocks.length === 0 ? (
            <p style={{ fontSize: 13, color: t.text3, margin: 0 }}>
              No constituents recorded today.
            </p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr>
                    {['Symbol', 'Today %', '5D %', 'Phase', 'Inst Flow 30B'].map(
                      (h, i) => (
                        <th
                          key={h}
                          style={{
                            padding: '10px 12px',
                            textAlign: i === 0 || i === 3 ? 'left' : 'right',
                            fontSize: 11,
                            fontWeight: 600,
                            letterSpacing: '0.08em',
                            textTransform: 'uppercase',
                            color: t.text3,
                            borderBottom: `1px solid ${t.border}`,
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {sector.top_stocks.map((s) => (
                    <tr key={s.symbol} style={{ borderTop: `1px solid ${t.border}` }}>
                      <td style={{ padding: '10px 12px' }}>
                        <Link
                          href={`/stock/${encodeURIComponent(s.symbol)}`}
                          style={{
                            color: t.text,
                            fontWeight: 600,
                            fontFamily: FONT_MONO,
                            textDecoration: 'none',
                          }}
                        >
                          {s.symbol}
                        </Link>
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: FONT_MONO }}>
                        <PctSpan value={s.today_pct} />
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: FONT_MONO }}>
                        <PctSpan value={s.pct_change_5d} />
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <PhaseTooltip tag={s.phase} onLearnMore={onPhaseLearnMore}>
                          <LifecycleTag tag={s.phase} />
                        </PhaseTooltip>
                      </td>
                      <td
                        style={{
                          padding: '10px 12px',
                          textAlign: 'right',
                          fontFamily: FONT_MONO,
                          color: s.inst_flow_score_30b > 0 ? t.bullish : t.text2,
                        }}
                      >
                        {s.inst_flow_score_30b > 0 ? '+' : ''}
                        {s.inst_flow_score_30b}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Block>

        <Block title="Institutional footprint">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 12,
            }}
          >
            <Stat
              label="Inst-buy bars (5d)"
              value={
                <span style={{ fontFamily: FONT_MONO, color: t.text, fontSize: 18, fontWeight: 600 }}>
                  {sector.inst_buy_bar_count_5d}
                </span>
              }
              note="Across all sector names"
            />
            <Stat
              label="Aggregate flow score"
              value={
                <span
                  style={{
                    fontFamily: FONT_MONO,
                    color: sector.inst_flow_total > 0 ? t.bullish : t.text2,
                    fontSize: 18,
                    fontWeight: 600,
                  }}
                >
                  {sector.inst_flow_total > 0 ? '+' : ''}
                  {sector.inst_flow_total}
                </span>
              }
              note={`Rank #${sector.rank_by_inst_flow} of ${totalSectorCount}`}
            />
          </div>
        </Block>

        <div style={{ padding: '6px 22px 22px' }}>
          <Link
            href={`/scanner?sector=${encodeURIComponent(sector.sector)}`}
            style={{
              display: 'inline-block',
              padding: '10px 16px',
              background: t.accent,
              color: t.bg,
              borderRadius: 8,
              fontWeight: 600,
              fontSize: 13,
              textDecoration: 'none',
            }}
          >
            Open scanner filtered to {sector.sector_label} →
          </Link>
        </div>
      </div>
    </section>
  );
}

function Block({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  const { t } = useTheme();
  return (
    <div style={{ padding: '16px 22px', borderBottom: `1px solid ${t.border}` }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          marginBottom: 10,
        }}
      >
        <h4
          style={{
            fontSize: 11,
            color: t.text3,
            fontFamily: FONT_MONO,
            fontWeight: 600,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            margin: 0,
          }}
        >
          {title}
        </h4>
        {hint && (
          <span
            style={{
              fontSize: 10,
              color: t.warning,
              fontFamily: FONT_MONO,
              padding: '2px 6px',
              border: `1px solid ${t.warning}`,
              borderRadius: 4,
              opacity: 0.8,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            {hint}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

function Stat({
  label,
  value,
  note,
}: {
  label: string;
  value: React.ReactNode;
  note?: string;
}) {
  const { t } = useTheme();
  return (
    <div>
      <div
        style={{
          fontSize: 11,
          color: t.text3,
          fontFamily: FONT_MONO,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 14 }}>{value}</div>
      {note && (
        <div style={{ fontSize: 11, color: t.text3, marginTop: 4 }}>{note}</div>
      )}
    </div>
  );
}

function PctSpan({ value }: { value: number }) {
  const { t } = useTheme();
  const pct = value * 100;
  const color = pct > 0 ? t.bullish : pct < 0 ? t.bearish : t.text2;
  return (
    <span style={{ color, fontWeight: 600 }}>
      {pct >= 0 ? '+' : ''}
      {pct.toFixed(2)}%
    </span>
  );
}

function DimSlash() {
  const { t } = useTheme();
  return <span style={{ color: t.text3 }}>·</span>;
}

function fmtRs(rs: number | null): string {
  if (rs === null) return '—';
  return rs.toFixed(2);
}

function BreadthBar({ value }: { value: number }) {
  const { t } = useTheme();
  const pct = Math.round(value * 100);
  const fill = value >= 0.6 ? t.bullish : value >= 0.4 ? t.text : t.bearish;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontFamily: FONT_MONO, color: t.text, fontSize: 16, fontWeight: 600 }}>
        {pct}%
      </span>
      <div
        style={{
          width: '100%',
          maxWidth: 160,
          height: 4,
          background: t.surface,
          borderRadius: 2,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: fill,
            opacity: 0.75,
          }}
        />
      </div>
    </div>
  );
}
