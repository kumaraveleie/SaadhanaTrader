import {
  readLatestScan,
  readResearchSnapshot,
  type ResearchRow,
} from '../lib/scan-data';
import { ResearchHeader } from './research-header';
import { StrengthDespiteWeaknessPanel } from './strength-despite-weakness';
import { Breakout52whPanel } from './breakout-52wh';
import { SectorStrengthPanel } from './sector-strength';
import { ResearchNoData } from './research-no-data';

export const dynamic = 'force-dynamic';

const NEAR_52WH_PCT = 0.05;

function filterStrengthDespiteWeakness(snap: { rows: ResearchRow[]; nifty_pct_change_today: number }): ResearchRow[] {
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
  // 52WH Breakout Watch — within 5% of 52WH, healthy momentum
  // (RSI 50-70 plus accumulation positive). Universe-wide; doesn't
  // require Nifty-down like the divergence panel.
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

export default async function ResearchPage() {
  const [snap, latest] = await Promise.all([
    readResearchSnapshot(),
    readLatestScan(),
  ]);

  if (snap === null) {
    return <ResearchNoData />;
  }

  const sdw = filterStrengthDespiteWeakness(snap);
  const breakouts = filterBreakout52wh(snap);
  // Regime is authoritative on latest.json (the §15 daily-scan output);
  // the research snapshot doesn't classify it. Fall back to Caution if
  // latest.json is missing — research is informational, not gating.
  const regime = latest?.regime ?? 'Caution';

  return (
    <div style={{ maxWidth: 1200, margin: '20px auto 60px' }}>
      <ResearchHeader
        scanDate={snap.scan_date}
        regime={regime}
        universeSize={snap.universe_size}
        rowsScanned={snap.rows.length}
        niftyPctChange={snap.nifty_pct_change_today}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 32, marginTop: 32 }}>
        <StrengthDespiteWeaknessPanel
          rows={sdw}
          niftyPctChange={snap.nifty_pct_change_today}
        />
        <Breakout52whPanel rows={breakouts} />
        <SectorStrengthPanel />
      </div>
    </div>
  );
}
