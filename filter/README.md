# filter — the Saadhana brain

Python module that implements the canonical filter rules from
[`spec/filter_spec_v2_1.md`](../spec/filter_spec_v2_1.md) (v2.1
Provisional, current contract). The previous v2.0 spec is preserved
as audit trail at [`spec/filter_spec_v2.md`](../spec/filter_spec_v2.md)
per §16 — frozen, read-only. This is the reference implementation;
the TypeScript mirror in `trader/app/lib/` and the Pine scripts in
`pine/` are validated against it via parity tests.

## Install (dev)

```bash
cd filter
python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows
pip install -e ".[dev]"
```

## Run tests

```bash
pytest                                       # full suite
pytest --cov=saadhana_filter --cov-report=term-missing
pytest tests/test_conditions.py -k stage_2   # one condition
```

Target coverage: **≥ 85% on `indicators/`, `signals/`, `forensics/`**.

## Layout

```
saadhana_filter/
├── data/         # OHLCV loaders (yfinance + Parquet cache)
├── indicators/   # 13 conditions, institutional flow, stage analysis
├── catalysts/    # corporate filings, shareholding, deals  (Phase D)
├── signals/      # BUY/HOLD/SELL/WAIT engine                (Phase C)
├── ledger/       # signal ledger schema + writers           (Phase H)
├── forensics/    # outcome tracker, cluster analyzer        (Phase I)
├── backtest/     # §11 validator                            (Phase G)
└── scan/         # daily scan entrypoint                    (Phase C)
```

Each condition is a pure function: takes a DataFrame, returns a
`pd.Series[bool]` aligned to the input index. No I/O, no globals, no
side effects. Docstrings reference the spec section (e.g. `"""§5.1 — …"""`).

## Conventions

- Type hints everywhere
- Tests live alongside in `tests/`, mirror source path
- Each condition has ≥ 3 tests: uptrend (true), downtrend (false), edge case
- Format with `ruff format`, lint with `ruff check`
- Commit with spec section: `feat(§5.3): institutional flow score`
