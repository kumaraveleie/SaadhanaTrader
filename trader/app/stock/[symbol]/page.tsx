import {
  readLatestScan,
  readResearchSnapshot,
  type CandidateRow,
  type ResearchRow,
} from '../../lib/scan-data';
import { StockHeader } from './stock-header';
import { PatternSection } from './pattern-section';
import { CatalystSection } from './catalyst-section';
import { StockNotMatched } from './stock-not-matched';

export const dynamic = 'force-dynamic';

type Params = { symbol: string };

export default async function StockDetailPage({ params }: { params: Params }) {
  const symbol = decodeURIComponent(params.symbol).toUpperCase();
  const [scan, research] = await Promise.all([
    readLatestScan(),
    readResearchSnapshot(),
  ]);

  // Pattern data lives on latest.json (only candidates). Catalyst +
  // sector + price data lives on research.json (all Tier-1-passing
  // symbols, candidate or not). The two are independent dimensions —
  // a symbol can have catalysts without a pattern match.
  const candidate: CandidateRow | null =
    scan?.candidates.find((c) => c.symbol.toUpperCase() === symbol) ?? null;
  const researchRow: ResearchRow | null =
    research?.rows.find((r) => r.symbol.toUpperCase() === symbol) ?? null;

  // 404 only when the symbol exists in neither scan — i.e. not in the
  // universe at all. (Previously we 404'd whenever the symbol was a
  // non-candidate, hiding the catalyst card; bug fixed here.)
  if (!candidate && !researchRow) {
    return (
      <StockNotMatched
        symbol={symbol}
        reason={!scan ? 'no_scan' : 'not_in_candidates'}
        regime={scan?.regime}
        scanDate={scan?.scan_date}
      />
    );
  }

  // Catalysts: prefer candidate (latest.json) if available, else
  // research row. Both carry the same per-symbol catalyst summary.
  const catalysts = candidate?.catalysts ?? researchRow?.catalysts ?? [];
  const highConviction =
    candidate?.has_high_conviction_catalyst ??
    researchRow?.has_high_conviction_catalyst ??
    false;

  const regime = scan?.regime ?? 'Caution';
  const scanDate = scan?.scan_date ?? research?.scan_date ?? '';

  return (
    <div style={{ maxWidth: 1100, margin: '20px auto 60px' }}>
      <StockHeader
        symbol={symbol}
        candidate={candidate}
        researchRow={researchRow}
        regime={regime}
        scanDate={scanDate}
      />
      <div
        style={{
          marginTop: 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 24,
        }}
      >
        <PatternSection
          candidate={candidate}
          regime={regime}
          scanDate={scanDate}
        />
        <CatalystSection
          catalysts={catalysts}
          highConviction={highConviction}
        />
      </div>
    </div>
  );
}
