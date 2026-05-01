'use client';

import { useTheme } from '../components/theme';
import { FreshnessIndicator } from '../components/freshness-indicator';
import { RegimeRibbon } from '../components/regime-ribbon';
import { SectorStrip } from '../components/sector-strip';
import { regimeLabel } from '../lib/labels';
import type { Regime, SectorStrength } from '../lib/scan-types';

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
  const label = regimeLabel(regime);
  const ribbonTooltip = `${label.tooltip}\n\nScan covers ${rowsScanned} of ${universeSize} stocks today.`;

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
          Markets
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
        Where strength is hiding today — sector rotation, divergent
        strength, breakout watch.
      </p>

      <RegimeRibbon
        regime={regime}
        niftyPctChange={niftyPctChange}
        tooltip={ribbonTooltip}
        footer={
          <SectorStrip
            sectors={sectors}
            selected={selectedSector}
            onSelect={onSelectSector}
          />
        }
      />
    </header>
  );
}
