# CLAUDE.md — Saadhana Trader

This file is the orientation document every Claude Code session inherits.
Read it first, every time, before touching the codebase.

**GitHub:** https://github.com/kumaraveleie/SaadhanaTrader
**Vercel target:** `saadhana-trader.vercel.app` (public) and a separate
private deploy for Personal mode
**Visual reference:** Optaur (https://optaur-demo.vercel.app/) — Saadhana
Trader belongs to the same product family. See `spec/design_system.md`.

## Project mission

Build an Indian cash-equity stock filtering and signal system that:
- Surfaces high-probability long candidates (≥5% upside, low drawdown risk)
- Generates explicit BUY/HOLD/SELL/WAIT signals with paired entry/stop/target
- Learns from its own losses via a forensics + shadow-mode rule promotion loop
- Ships as a public research dashboard (Saadhana Trader) AND a private
  trading dashboard (Saadhana Personal) on the same codebase, gated by auth

**The single source of truth is `spec/filter_spec_v2_1.md`.** Read it end
to end before writing code. Every commit message references the section
number it implements (e.g., "feat(§5.3): institutional flow score").
`spec/filter_spec_v2.md` is the v2.0 audit trail — frozen, read-only.

**The visual contract is `spec/design_system.md`.** Saadhana Trader looks
and feels like Optaur — same dark theme, same neon-green accent, same
typography, same brand-mark construction. Different glyph, same DNA.
Visual drift is a bug — propagate design changes to all components in
the same PR.

## Architecture in one screen

```
Filter brain (Python)  →  Storage (Vercel Postgres)  →  Trader app (Next.js on Vercel)
       ↑                                                          ↓
       └─ Pine mirrors (TradingView, chart-side visualization) ───┘
```

Three layers, ONE shared spec. Drift between them is caught by parity tests.

## Repo layout

```
saadhana-trader/
├── README.md                    # public-facing project description
├── CLAUDE.md                    # THIS FILE — orientation for Claude Code
├── HANDOFF_PROMPT.md            # exact prompt to start a Claude Code session
├── .gitignore
├── .github/
│   └── workflows/               # GitHub Actions cron jobs (Phase M)
├── spec/
│   ├── filter_spec_v2_1.md      # ← canonical spec (v2.1 Provisional)
│   ├── filter_spec_v2.md        # v2.0 audit trail (frozen)
│   ├── thinking_engine.md       # Thinking Engine roadmap (M1–M4)
│   ├── candidate_rules.md       # CR-001..CR-008 — parked rule ideas
│   ├── design_system.md         # visual contract
│   └── samples/
│       └── weekly_review_example.md
├── filter/                      # Python module — the brain
│   ├── pyproject.toml
│   ├── README.md
│   ├── saadhana_filter/
│   │   ├── __init__.py
│   │   ├── data/                # OHLCV loaders (yfinance, bhavcopy)
│   │   ├── indicators/          # 13 conditions, institutional flow, stage
│   │   ├── catalysts/           # Phase D — 5 deterministic sources
│   │   │   ├── types.py             # taxonomy + freshness + dataclasses
│   │   │   ├── classifier.py        # filing-text classifier
│   │   │   ├── aggregator.py        # per-symbol merge_sources
│   │   │   ├── daily.py             # build_all_catalysts orchestrator
│   │   │   └── sources/             # bse_filings / shareholding /
│   │   │                            # block_deals / insider_trades /
│   │   │                            # sector_momentum (Phase D2 swap
│   │   │                            # fixture fetchers for live scrapers)
│   │   ├── sectors/             # M1 v0 sector strength (catalyst rollup)
│   │   ├── signals/             # BUY/HOLD/SELL/WAIT engine
│   │   ├── ledger/              # signal ledger schema + writers
│   │   ├── forensics/           # outcome tracker, cluster analyzer
│   │   ├── backtest/            # §11 validator
│   │   └── scan/                # daily scan entrypoint
│   └── tests/
│       ├── conftest.py          # shared fixtures (synthetic OHLCV)
│       ├── fixtures/            # CSV fixtures (uptrend/downtrend/sideways)
│       └── test_*.py
├── trader/                      # Next.js app — the public face
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx             # hero / today's top picks preview
│   │   ├── scanner/page.tsx     # main screener
│   │   ├── stock/[symbol]/page.tsx
│   │   ├── learning/page.tsx    # forensics review (PERSONAL only)
│   │   ├── api/
│   │   │   ├── scan/route.ts    # reads cached scan results
│   │   │   ├── stock/[symbol]/route.ts
│   │   │   └── auth/...         # NextAuth routes
│   │   └── lib/
│   │       ├── indicators/      # TS mirror of Python indicators
│   │       ├── data/            # fetcher + cache reader
│   │       ├── design/          # tokens (carried from Optaur)
│   │       └── auth/
│   └── ...
├── pine/                        # Pine scripts (TradingView mirror)
│   ├── saadhana_pro_setups.pine
│   └── saadhana_volume_v2.pine
└── scripts/
    ├── daily_scan.py            # GitHub Actions entrypoint (Phase M)
    └── weekly_forensics.py      # forensics weekly review entrypoint
```

## Tech stack

| Layer | Stack | Why |
|---|---|---|
| Filter brain | Python 3.11, pandas, numpy, pyarrow, pytest | Standard for indicator math, easy testing |
| Catalyst engine | Python + httpx + lxml | Scrape filings; small LLM via HF Space later |
| Storage | Vercel Postgres | Free, integrates with Next.js, hosts both auth + scan data |
| Cron compute | GitHub Actions | Free, scheduled, no cold-start issue (it's not user-facing) |
| LLM (Phase E) | Hugging Face Space, Qwen 7B / Phi-4 | Free CPU tier, 16 GB |
| Frontend | Next.js 14 App Router, TypeScript, Tailwind | Same as Optaur for design-system reuse |
| Auth | NextAuth (credentials provider) | Free, simple, fits Vercel |
| Charts | lightweight-charts (TradingView's lib) | Same look as TV without the closed platform |
| Personal dashboard | Streamlit (local) | Optional — for full BUY/SELL view on owner's laptop |

## Conventions

### Python
- **Type hints everywhere.** `def cond_x(df: pd.DataFrame) -> pd.Series:`
- **Pure functions for indicators.** Take DataFrame, return Series/DataFrame.
  No side effects, no globals, no I/O inside.
- **Docstrings reference the spec section.** First line of every condition:
  `"""§5.1 — 5-EMA > 20-EMA AND 5-EMA rising."""`
- **Tests live alongside code.** `tests/test_<module>.py` mirrors source path.
- **Each condition has at least 3 tests:** uptrend (true), downtrend (false),
  edge case (boundary).
- **Format with `ruff format`. Lint with `ruff check`.** Pre-commit hook.

### TypeScript
- **Mirror Python condition by condition.** Same name, same signature shape.
- **Parity test:** for each TS condition, a test loads a CSV fixture and
  asserts the TS output matches the Python output to ≤1e-6 tolerance.
- **No `any`. Strict mode on.** ESLint with `@typescript-eslint/strict`.

### Naming
- Conditions: `cond_<short_snake_case>` matching spec section
- Catalysts: `catalyst_<type>` matching §13.1 taxonomy
- Signal states: `BUY`, `HOLD`, `SELL`, `WAIT` (uppercase, internal)
- Public labels: come from `lib/labels.ts` mapping table — never hardcoded

### Commits
- Format: `<type>(§<spec-section>): <imperative summary>`
  - Examples: `feat(§5.3): institutional flow score`,
    `test(§5.1): add downtrend fixture`,
    `fix(§14): conviction tier threshold off-by-one`
- One spec section per commit when feasible
- Tests in same commit as implementation; never "tests in next commit"
- Run `pytest` before every commit. Pre-commit hook enforces.

### Testing discipline
- **Golden-fixture tests** for every condition: synthetic OHLCV CSV with
  known shape, asserts known output
- **Parity tests** between Python and TypeScript: 5 real-world tickers,
  200 bars each, exported to CSV; both implementations must agree
- **Backtest replay** uses ONLY data available on the scan date.
  Lookahead bias is the #1 silent bug — guard against it explicitly
- **Coverage target:** ≥85% on `indicators/`, `signals/`, `forensics/`

## What goes where (decision rules)

- **A condition or rule of the spec → both `filter/` and `trader/app/lib/`.**
  Python is canonical; TypeScript is the mirror.
- **Catalyst sources → `filter/saadhana_filter/catalysts/` only.**
  Frontend reads catalyst tags from cached JSON, doesn't recompute.
- **Backtest, forensics, ledger writes → Python only.**
  Heavy compute. Frontend reads results from Postgres.
- **UI logic, charts, auth, label translation → `trader/` only.**
- **Pine script updates → `pine/` only**, mirrored to spec by hand
  (no automated transpilation in v2).

## Public vs Personal mode

The Next.js app reads `NEXT_PUBLIC_MODE=public|personal` at build time:
- `public` → hides position sizing, hides /learning, applies §21.1 label map
- `personal` → shows everything, uses internal labels

Two Vercel projects deploy from the same repo: `saadhana-trader` (public,
custom domain) and `saadhana-personal` (private, password-walled). The
build-time env var differs; the codebase is one.

## Compliance reminders

- **Never hardcode** "BUY" or "SELL" in user-facing JSX. Always go through
  `lib/labels.ts`.
- **Disclaimer banner is a layout-level component**, not a per-page choice.
  Editing it requires touching `app/layout.tsx`.
- **No personalized advice ever in public mode.** Public sees patterns and
  data; users do their own research.

## Known gotchas

- **OneDrive locks files randomly.** This repo lives at
  `C:\Kumaravel\AIBuilder\Saadhana\saadhana-trader\` (NOT in OneDrive)
  to avoid sync interference during npm install / git operations.
- **Pine v6 forbids multi-line ternaries inside conditional blocks.**
  Extract to a function. See `pine/saadhana_pro_setups.pine` precedent.
- **yfinance rate-limits aggressive scanning.** The daily scan caches
  to Parquet; never call yfinance from a request handler.
- **Vercel serverless 10s timeout.** Anything heavier runs in GitHub Actions,
  not in `app/api/`.

## Where to find things

- **The contract:** `spec/filter_spec_v2_1.md` (canonical)
- **Audit trail:** `spec/filter_spec_v2.md` (v2.0, frozen)
- **Thinking Engine roadmap:** `spec/thinking_engine.md`
- **Candidate rules registry:** `spec/candidate_rules.md`
- **The visual contract:** `spec/design_system.md`
- **What to build next:** §23 of the spec lists phases A through N
- **Pine scripts (chart-side visual checklist — NOT a Python mirror):**
  `pine/saadhana_pro_setups.pine` and `pine/saadhana_volume_v2.pine`.
  These compute a **different** 13-condition set inherited from
  Mashrani Pro-Setups (Ichimoku cloud, DCR/WCR, U/D ratio, ATH proximity,
  IV-day tracking). Pine and Python are **intentionally not 1:1** — see
  the explanatory note at the top of spec §5. Do **not** "fix" one to
  match the other; they are separate systems serving different purposes
  (Pine = what a human eyeballs on a TradingView chart, Python = what
  the signal engine decides). The Pine-only signals are parked as future
  shadow-mode candidates per §19.5.
- **Optaur source files (parent design reference):**
  `C:\Kumaravel\AIBuilder\Saadhana\freelance-bids\options-trading-platform\optaur-demo\`
  — read `app/components/theme.tsx`, `app/components/nav.tsx`,
  `app/components/brand-mark.tsx`, `app/globals.css`, `app/layout.tsx`
  to understand the construction patterns. Then mirror them in
  `trader/app/` per `spec/design_system.md` §8

## How to start work in a fresh Claude Code session

1. Read `spec/filter_spec_v2_1.md` cover to cover (it's the contract)
2. Read this file (CLAUDE.md)
3. Read the most recent commits to see what's been done
4. Pick the next phase from §23 that isn't yet complete
5. Implement, test, commit with spec-section-tagged message
6. Run `pytest` (Python) and `npm test` (TypeScript) before push
7. Update phase status in this CLAUDE.md as phases complete

## Out of scope (don't build without explicit ask)

Anything in spec §22. Specifically: short-side signals, intraday timing,
options overlay, real-time tick data, mobile-native app, multi-user paper
trading. The system is deliberately small in v2.

---

**This file is updated when architecture decisions change. Code-only
changes do NOT update this file. The spec is the contract; CLAUDE.md
is the orientation.**
