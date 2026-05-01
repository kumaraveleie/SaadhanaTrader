import { readLatestScan, type CandidateRow } from '../../lib/scan-data';
import { StockHeader } from './stock-header';
import { ConditionChecklist } from './condition-checklist';
import { RiskLevelsCard } from './risk-levels-card';
import { StockNotMatched } from './stock-not-matched';
import { CatalystCard } from './catalyst-card';

export const dynamic = 'force-dynamic';

type Params = { symbol: string };

export default async function StockDetailPage({ params }: { params: Params }) {
  const symbol = decodeURIComponent(params.symbol).toUpperCase();
  const scan = await readLatestScan();

  if (scan === null) {
    return <StockNotMatched symbol={symbol} reason="no_scan" />;
  }

  const candidate: CandidateRow | undefined = scan.candidates.find(
    (c) => c.symbol.toUpperCase() === symbol,
  );

  if (!candidate) {
    return (
      <StockNotMatched
        symbol={symbol}
        reason="not_in_candidates"
        regime={scan.regime}
        scanDate={scan.scan_date}
      />
    );
  }

  const catalysts = candidate.catalysts ?? [];
  return (
    <div style={{ maxWidth: 1100, margin: '20px auto 60px' }}>
      <StockHeader candidate={candidate} scanDate={scan.scan_date} />
      <div
        className="saadhana-stock-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)',
          gap: 24,
          marginTop: 32,
        }}
      >
        <ConditionChecklist failedConditions={candidate.failed_conditions} />
        <RiskLevelsCard candidate={candidate} />
      </div>
      {catalysts.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <CatalystCard
            catalysts={catalysts}
            highConviction={candidate.has_high_conviction_catalyst ?? false}
          />
        </div>
      )}
    </div>
  );
}
