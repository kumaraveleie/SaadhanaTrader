'use client';

import { useTheme } from './theme';
import type { SectorStrength } from '../lib/scan-types';

const FONT_MONO = 'var(--font-mono), "JetBrains Mono", ui-monospace, monospace';

/**
 * Sector mini-strip — top-3 strongest sectors (by today's % change),
 * rendered as clickable chips inside the regime ribbon. Clicking a
 * chip emits onSelect(sector_slug); the /research page coordinates the
 * inline drill panel.
 */
export function SectorStrip({
  sectors,
  selected,
  onSelect,
}: {
  sectors: SectorStrength[];
  selected: string | null;
  onSelect: (sector: string | null) => void;
}) {
  const { t } = useTheme();
  const top = sectors.slice(0, 3);
  if (top.length === 0) {
    return (
      <span style={{ color: t.text3, fontFamily: FONT_MONO, fontSize: 12 }}>
        Sector strength snapshot unavailable.
      </span>
    );
  }
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 6,
      }}
    >
      <span style={{ color: t.text3, fontFamily: FONT_MONO, fontSize: 11, marginRight: 4 }}>
        Strongest today:
      </span>
      {top.map((s) => (
        <SectorChip
          key={s.sector}
          sector={s}
          active={selected === s.sector}
          onClick={() => onSelect(selected === s.sector ? null : s.sector)}
        />
      ))}
    </div>
  );
}

function SectorChip({
  sector,
  active,
  onClick,
}: {
  sector: SectorStrength;
  active: boolean;
  onClick: () => void;
}) {
  const { t } = useTheme();
  const pct = sector.today_pct * 100;
  const tone = pct > 0 ? t.bullish : pct < 0 ? t.bearish : t.text2;
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 10px',
        background: active ? t.surface : 'transparent',
        border: `1px solid ${active ? t.accent : t.border}`,
        borderRadius: 999,
        fontSize: 12,
        color: t.text,
        fontFamily: FONT_MONO,
        cursor: 'pointer',
        fontWeight: 500,
        transition: 'border-color 80ms ease, background 80ms ease',
      }}
    >
      <span>{sector.sector_label}</span>
      <span style={{ color: tone, fontWeight: 600 }}>
        {pct >= 0 ? '+' : ''}
        {pct.toFixed(1)}%
      </span>
    </button>
  );
}
