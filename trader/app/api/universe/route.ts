import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { NextResponse } from 'next/server';
import { readResearchSnapshot } from '../../lib/scan-data';

export const dynamic = 'force-dynamic';

/**
 * Universe API for the nav SymbolSearch dropdown.
 *
 * Returns the list of symbols scanned today, joined with company
 * names from `data/nifty500_constituents.csv`. Server-side reads
 * keep the CSV out of the client bundle (it's ~25KB raw; with
 * gzip, the JSON response is much smaller and only fetched on
 * first search interaction).
 */
type UniverseSymbol = {
  symbol: string;
  name: string | null;
  sub_industry: string;
  close: number;
};

async function readNamesCSV(): Promise<Map<string, string>> {
  const path = join(
    process.cwd(),
    '..',
    'data',
    'nifty500_constituents.csv',
  );
  try {
    const text = await readFile(path, 'utf-8');
    const lines = text.split(/\r?\n/).slice(1).filter(Boolean);
    const map = new Map<string, string>();
    for (const line of lines) {
      // CSV format: Symbol,Company Name,Industry,Series,ISIN Code
      // No quoted commas observed in the NSE-supplied file.
      const parts = line.split(',');
      if (parts.length < 2) continue;
      const symbol = parts[0]?.trim();
      const name = parts[1]?.trim();
      if (symbol && name) map.set(symbol, name);
    }
    return map;
  } catch {
    return new Map();
  }
}

export async function GET() {
  const [snap, names] = await Promise.all([
    readResearchSnapshot(),
    readNamesCSV(),
  ]);
  if (snap === null) {
    return NextResponse.json({ symbols: [], scan_date: null });
  }
  const symbols: UniverseSymbol[] = snap.rows.map((r) => ({
    symbol: r.symbol,
    name: names.get(r.symbol) ?? null,
    sub_industry: r.sub_industry,
    close: r.close_today,
  }));
  // Stable alphabetical sort for client-side filtering predictability.
  symbols.sort((a, b) => a.symbol.localeCompare(b.symbol));
  return NextResponse.json(
    { symbols, scan_date: snap.scan_date },
    {
      headers: {
        // Keep cache short — scan output rotates daily; client requests
        // typically come on first nav interaction so a tiny TTL is fine.
        'Cache-Control': 'public, max-age=60, s-maxage=300',
      },
    },
  );
}
