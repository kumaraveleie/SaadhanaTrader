/**
 * Server-side reader for ``signals/latest.json``.
 *
 * This module imports Node built-ins and MUST NOT be pulled into a
 * client component. Client-safe types live in ``./scan-types``.
 */

import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import type { ScanResult } from './scan-types';

export type { CandidateRow, Regime, ScanResult, SignalState } from './scan-types';

function latestJsonPath(): string {
  // ``trader/`` is the project root for the Next.js app. The scan output
  // lives at ``<repo-root>/signals/latest.json`` — one level above.
  return join(process.cwd(), '..', 'signals', 'latest.json');
}

export async function readLatestScan(): Promise<ScanResult | null> {
  try {
    const raw = await readFile(latestJsonPath(), 'utf-8');
    return JSON.parse(raw) as ScanResult;
  } catch {
    return null;
  }
}
