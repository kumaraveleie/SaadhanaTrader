import { readResearchSnapshot, readLatestScan } from './lib/scan-data';
import { HomeClient } from './home-client';

export const dynamic = 'force-dynamic';

const TOP_SECTOR_COUNT = 3;

export default async function HomePage() {
  // Pull regime from latest.json (the §15 daily-scan output, where the
  // regime classifier lives). Pull sector aggregates from research.json
  // (where the M1 v0 sector strength engine emits `sector_strength`).
  // Both are best-effort — home gracefully omits the ribbon when
  // either file is missing.
  const [latest, research] = await Promise.all([
    readLatestScan(),
    readResearchSnapshot(),
  ]);

  const regime = latest?.regime ?? null;
  const niftyPctChange = research?.nifty_pct_change_today ?? null;
  const topSectors = research?.sector_strength.slice(0, TOP_SECTOR_COUNT) ?? [];

  return (
    <HomeClient
      regime={regime}
      niftyPctChange={niftyPctChange}
      topSectors={topSectors}
    />
  );
}
