# Handoff prompt — paste this into Claude Code in VS Code

Copy everything between the `---BEGIN---` and `---END---` markers below
into your first Claude Code message after opening this repo in VS Code.

---BEGIN---

You're picking up the Saadhana Trader project. Before writing any code,
follow these orientation steps in order:

1. Read `spec/filter_spec_v2.md` cover to cover. It is the canonical
   contract. Every line of code you write must trace back to a section
   in this spec.

2. Read `CLAUDE.md` for repo conventions, tech stack, layout, and
   the public/personal mode split.

3. Read the existing Pine scripts at `pine/saadhana_pro_setups.pine`
   and `pine/saadhana_volume_v2.pine`. These are the working reference
   for the 13 technical conditions and the institutional flow logic.
   Port them faithfully to Python and TypeScript.

4. Look at `git log --oneline` to see what's been committed so far.

Then check spec §23 (build phases A–N). The phases that are NOT yet
complete in the repo are your work queue. Start with the earliest
incomplete phase. Specifically — if no Python code exists yet, start
with **Phase B**:

> **Phase B — Python data loader + 13 technical conditions + tests**
> Definition of done: all 13 conditions pass golden-fixture tests.

Implementation order for Phase B:

1. Set up `filter/pyproject.toml` with dependencies: pandas, numpy,
   pyarrow, yfinance, pytest, pytest-cov, ruff, hypothesis.
2. Build `filter/saadhana_filter/data/loader.py` — yfinance EOD pull
   with Parquet cache at `~/.saadhana/data/eod/`.
3. Build `filter/tests/conftest.py` with synthetic OHLCV fixtures:
   `uptrend_fixture`, `downtrend_fixture`, `sideways_fixture`,
   `breakout_fixture`. Use deterministic seeds for reproducibility.
4. Implement the 13 conditions in `filter/saadhana_filter/indicators/
   conditions.py`. Each condition is a pure function:
   ```python
   def cond_5dema_above_20ema_rising(df: pd.DataFrame) -> pd.Series:
       """§5.1 — 5-EMA > 20-EMA AND 5-EMA rising bar-over-bar."""
       ...
   ```
5. Each condition gets at least 3 tests in `filter/tests/test_conditions
   .py`: uptrend (true), downtrend (false), edge case (boundary).
6. Implement `pro_setup_score()` aggregator that sums conditions.
7. Implement `cond_institutional_flow()` and `cond_inst_flow_score()`
   per spec §5.3.
8. Run `pytest --cov=saadhana_filter` and ensure ≥ 85% coverage on the
   indicators module.
9. Commit each condition individually with message format
   `feat(§5.X): <condition name>`.

After Phase B passes, proceed to Phase C (signal engine + Tier 1 gate),
then through phases D–N in order.

**Hard rules — do not violate**:

- Spec §17: signal ledger is APPEND-ONLY. Never modify a frozen signal
  fingerprint. If catalyst classification changes later, that affects
  future signals only, never the historical record.
- Spec §11: backtest validator uses ONLY data available on the scan
  date. No lookahead bias. Catalyst data must use point-in-time freezes.
- Spec §21: Public mode never says BUY/SELL. Always go through
  `lib/labels.ts` mapping. The disclaimer banner is layout-level, not
  per-page.
- Drift between Python, TypeScript, and Pine implementations is caught
  by parity tests. Update all three when changing a rule.

**Commit format**:
- `feat(§<section>): <imperative>` for new features
- `test(§<section>): <imperative>` for tests
- `fix(§<section>): <imperative>` for bug fixes
- `docs: <imperative>` for non-spec documentation
- One spec section per commit when feasible

**Before each commit**: run `pytest` (Python) and `npm test`
(TypeScript when present) and ensure both pass.

Begin.

---END---

## Notes for the operator (Kumaravel)

- The handoff prompt is what Claude Code reads on its first message.
  Subsequent messages can be normal "continue with phase C" or "fix the
  test that's failing on cond_rsi_50_70" — Claude Code remembers
  the spec and conventions from the first read.
- If you change the spec, paste the relevant section into the next
  Claude Code message and explicitly say "spec updated, propagate to
  Python and TS."
- The `/learning` page in Saadhana Personal will eventually have an
  "Approve / Reject" button for forensics-proposed rule changes.
  Approval is your job — never delegate that to the LLM.
- Vercel deploy will auto-trigger on push to main. Configure the GitHub
  → Vercel integration once at the start.
- Phase G (backtest validator) is the GO/NO-GO gate. Do not put a single
  rupee of real capital behind this system until §11 passes.
