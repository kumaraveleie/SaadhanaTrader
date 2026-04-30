import { readLatestScan, type Regime, type ScanResult } from '../lib/scan-data';
import { ScannerTable } from './scanner-table';
import { ScannerHeader, ScannerEmptyState, ScannerNoData } from './scanner-states';

// Force dynamic rendering so the JSON file is re-read on every request
// in dev. Production behavior on Vercel re-reads on each cold start;
// the Phase M cron rewrites latest.json out-of-band.
export const dynamic = 'force-dynamic';

export default async function ScannerPage() {
  const data: ScanResult | null = await readLatestScan();

  if (data === null) {
    return <ScannerNoData />;
  }

  const { scan_date, regime, universe_size, candidates } = data;

  return (
    <div style={{ maxWidth: 1100, margin: '20px auto 60px' }}>
      <ScannerHeader
        scanDate={scan_date}
        regime={regime}
        universeSize={universe_size}
        candidatesCount={candidates.length}
      />
      {candidates.length === 0 ? (
        <ScannerEmptyState regime={regime} />
      ) : (
        <ScannerTable candidates={candidates} />
      )}
    </div>
  );
}
