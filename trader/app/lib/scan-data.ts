/**
 * Server-side reader for ``signals/latest.json``.
 *
 * This module imports Node built-ins and MUST NOT be pulled into a
 * client component. Client-safe types live in ``./scan-types``.
 */

import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import type { ResearchSnapshot, ScanResult } from './scan-types';

export type {
  CandidateRow,
  Catalyst,
  CatalystRollup,
  CatalystType,
  FreshnessTag,
  LifecycleTag,
  Regime,
  ResearchRow,
  ResearchSnapshot,
  ScanResult,
  SectorCatalystHighlight,
  SectorStrength,
  SectorTopStock,
  SignalState,
} from './scan-types';

function signalsPath(file: string): string {
  // ``trader/`` is the project root for the Next.js app. Signal files
  // live at ``<repo-root>/signals/`` — one level above.
  return join(process.cwd(), '..', 'signals', file);
}

export async function readLatestScan(): Promise<ScanResult | null> {
  try {
    const raw = await readFile(signalsPath('latest.json'), 'utf-8');
    return JSON.parse(raw) as ScanResult;
  } catch {
    return null;
  }
}

export async function readResearchSnapshot(): Promise<ResearchSnapshot | null> {
  try {
    const raw = await readFile(signalsPath('research.json'), 'utf-8');
    return JSON.parse(raw) as ResearchSnapshot;
  } catch {
    return null;
  }
}
