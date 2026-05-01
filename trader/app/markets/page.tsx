import { readLatestScan, readResearchSnapshot } from '../lib/scan-data';
import { ResearchPageClient } from './research-client';
import { ResearchNoData } from './research-no-data';

export const dynamic = 'force-dynamic';

export default async function ResearchPage() {
  const [snap, latest] = await Promise.all([
    readResearchSnapshot(),
    readLatestScan(),
  ]);

  if (snap === null) {
    return <ResearchNoData />;
  }

  // Regime is authoritative on latest.json (the §15 daily-scan output);
  // the research snapshot doesn't classify it. Fall back to Caution if
  // latest.json is missing — research is informational, not gating.
  const regime = latest?.regime ?? 'Caution';

  return <ResearchPageClient snap={snap} regime={regime} />;
}
