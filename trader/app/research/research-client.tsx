'use client';

import { useState } from 'react';
import { ResearchHeader } from './research-header';
import { StrengthDespiteWeaknessPanel } from './strength-despite-weakness';
import { Breakout52whPanel } from './breakout-52wh';
import { SectorDrill } from '../components/sector-drill';
import { PhaseDrawer } from '../components/phase-drawer';
import type { Regime, ResearchRow, ResearchSnapshot } from '../lib/scan-types';

const NEAR_52WH_PCT = 0.05;

function filterStrengthDespiteWeakness(snap: {
  rows: ResearchRow[];
  nifty_pct_change_today: number;
}): ResearchRow[] {
  if (snap.nifty_pct_change_today >= 0) return [];
  const matches = snap.rows.filter(
    (r) => r.pct_change_today > 0 && r.dist_from_52wh_pct >= -NEAR_52WH_PCT,
  );
  const order: Record<ResearchRow['lifecycle'], number> = {
    INITIAL: 0,
    CONFIRMED: 1,
    LATE: 2,
    UNKNOWN: 3,
  };
  return [...matches].sort(
    (a, b) =>
      order[a.lifecycle] - order[b.lifecycle] ||
      b.dist_from_52wh_pct - a.dist_from_52wh_pct,
  );
}

function filterBreakout52wh(snap: { rows: ResearchRow[] }): ResearchRow[] {
  return [...snap.rows]
    .filter(
      (r) =>
        r.dist_from_52wh_pct >= -NEAR_52WH_PCT &&
        r.rsi_14 >= 50 &&
        r.rsi_14 <= 75 &&
        r.inst_flow_score_30b > 0,
    )
    .sort((a, b) => b.dist_from_52wh_pct - a.dist_from_52wh_pct)
    .slice(0, 20);
}

export function ResearchPageClient({
  snap,
  regime,
}: {
  snap: ResearchSnapshot;
  regime: Regime;
}) {
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const sdw = filterStrengthDespiteWeakness(snap);
  const breakouts = filterBreakout52wh(snap);
  const activeSector =
    selectedSector === null
      ? null
      : snap.sector_strength.find((s) => s.sector === selectedSector) ?? null;

  return (
    <div style={{ maxWidth: 1200, margin: '20px auto 60px' }}>
      <ResearchHeader
        scanDate={snap.scan_date}
        regime={regime}
        universeSize={snap.universe_size}
        rowsScanned={snap.rows.length}
        niftyPctChange={snap.nifty_pct_change_today}
        sectors={snap.sector_strength}
        selectedSector={selectedSector}
        onSelectSector={setSelectedSector}
      />

      {activeSector && (
        <div style={{ marginTop: 20 }}>
          <SectorDrill
            sector={activeSector}
            totalSectorCount={snap.sector_strength.length}
            onClose={() => setSelectedSector(null)}
            onPhaseLearnMore={() => setDrawerOpen(true)}
          />
        </div>
      )}

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 32,
          marginTop: activeSector ? 12 : 32,
        }}
      >
        <StrengthDespiteWeaknessPanel
          rows={sdw}
          niftyPctChange={snap.nifty_pct_change_today}
          onPhaseHelp={() => setDrawerOpen(true)}
        />
        <Breakout52whPanel
          rows={breakouts}
          onPhaseHelp={() => setDrawerOpen(true)}
        />
      </div>

      <PhaseDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
