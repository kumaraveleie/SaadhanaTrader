# Saadhana Trader

**Repository:** https://github.com/kumaraveleie/SaadhanaTrader
**Live (target):** https://saadhana-trader.vercel.app
**Visual family:** Optaur (https://optaur-demo.vercel.app/)

Indian cash-equity stock filtering and signal system. Surfaces
high-probability long candidates with paired entry, stop, and target
levels — and learns from its own losses via a forensics + shadow-mode
rule promotion loop.

> Saadhana Trader is a research and pattern-detection tool. Information
> only. Not investment advice. We are not registered with SEBI as an
> Investment Advisor or Research Analyst. Do your own research and
> consult a SEBI-registered advisor before making investment decisions.

## What it does

- Scans Nifty 500 daily and surfaces stocks meeting all 13 technical
  Pro-Setup conditions PLUS a Tier 1 fundamental quality gate
- Searches each candidate for a real catalyst (earnings beat, FII
  buying, buyback, management change, policy tailwind, sector momentum)
- Computes a conviction tier when technical + catalyst converge
- Provides explicit risk/target levels and a 3-tier profit ladder
- Logs every signal with full feature snapshot for post-hoc analysis
- Generates weekly forensics reviews and proposes rule improvements
- Promotes rule changes only after 30+ days of shadow-mode validation
  AND human approval

## Repo layout

See `CLAUDE.md` for the full layout. Top-level:

- `spec/filter_spec_v2.md` — the canonical contract
- `spec/design_system.md` — the visual contract (colors, type, components)
- `filter/` — Python brain (indicators, signals, forensics, backtest)
- `trader/` — Next.js app (public scanner + personal dashboard)
- `pine/` — TradingView Pine Script mirrors
- `scripts/` — GitHub Actions cron entrypoints

## Quick start (local dev)

```bash
# Python brain
cd filter
python -m venv .venv
.venv\Scripts\activate              # Windows
pip install -e ".[dev]"
pytest

# Next.js app
cd trader
npm install
npm run dev                         # localhost:3000
```

## Build phases

See spec §23. Currently at **Phase A — scaffold complete, spec locked**.
Next: Phase B (Python data loader + 13 conditions + tests).

## Compliance & legal

The codebase ships in two modes:

- **`saadhana-trader.vercel.app`** (public): research dashboard, soft
  language, login-walled, full disclaimer banner
- **Personal dashboard** (private): full BUY/SELL system, owner-only

Pre-launch step: ₹15–25k consultation with Indian securities law firm
to confirm public framing complies with research-analyst safe harbor.

## License

Private. Personal use. Do not redistribute.
