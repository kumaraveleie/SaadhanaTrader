# External Pine references — Triple confluence cohort

These three Pine scripts are the **authoritative source** for the Triple
confluence cohort's three component indicators. Our Python ports
(`filter/saadhana_filter/indicators/`) are clean-room reimplementations of
the math in these files.

| Indicator | Author | Pine file | Python port | Spec section |
|---|---|---|---|---|
| Ultimate MA | ChrisMoody | `ultimate_ma_chrismoody.pine` | `ma_crossover.py` | Sec.5.7 |
| ML Adaptive SuperTrend | AlgoAlpha | `ml_adaptive_supertrend_algoalpha.pine` | `adaptive_supertrend.py` | Sec.5.8 |
| Deviation Trend | BigBeluga | `deviation_trend_bigbeluga.pine` | `deviation_trend.py` | Sec.5.9 |

## Attribution policy

- These algorithms are NOT our work. We do not claim authorship.
- Our Python ports are independent reimplementations from the published Pine source.
- The TradingView deep-link UI on `/stock/[symbol]` displays:
  > Powered by Ultimate MA (ChrisMoody) · ML Adaptive SuperTrend (AlgoAlpha) · Deviation Trend (BigBeluga)
- License compliance:
  - ChrisMoody: open-source, no specific license declared
  - AlgoAlpha: Mozilla Public License 2.0
  - BigBeluga: CC BY-NC-SA 4.0 (non-commercial — review before any paid-tier launch)

## Verification protocol

Whenever any indicator's Python port is modified, the diff must be reviewed
against the corresponding Pine source in this folder. Documented divergences
(intentional simplifications or bug fixes) go in the Python module's docstring.

If a divergence is unintentional, fix the Python port to match the Pine source.
If the Pine source itself appears to have a bug, document it in the port's
docstring AND open an issue noting the discrepancy.
