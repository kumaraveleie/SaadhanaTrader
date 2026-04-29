"""§12 — market regime filter on the Nifty 50 close.

A long-only system cannot make money in a true bear market. The regime
classifier inspects the index daily and shapes the rest of the engine:

| State        | Condition                                              | Effect                                                       |
|--------------|--------------------------------------------------------|--------------------------------------------------------------|
| ``Risk_On``  | close > 50-DMA AND close > 200-DMA AND 50-DMA rising   | BUYs enabled, normal sizing                                  |
| ``Caution``  | close between 50-DMA and 200-DMA                       | BUYs require Score 13/13 + HIGH conviction (§14, Phase F)    |
| ``Risk_Off`` | close < 200-DMA                                        | BUYs disabled; HOLDs reviewed with tighter stops (§8)        |

The classifier runs on a daily index OHLCV frame so backtests (§11)
can replay regime history.
"""

from __future__ import annotations

from enum import StrEnum

import pandas as pd

from saadhana_filter.indicators.primitives import sma


class Regime(StrEnum):
    RISK_ON = "Risk_On"
    CAUTION = "Caution"
    RISK_OFF = "Risk_Off"


def market_regime(nifty_df: pd.DataFrame) -> pd.Series:
    """Per-bar regime classification on the Nifty 50 OHLCV frame.

    ``nifty_df`` must carry at least a ``close`` column with a
    business-day ``DatetimeIndex``. Returns a ``pd.Series[Regime]``
    aligned to the input index. Bars without enough lookback (< 200
    bars) resolve to ``Caution`` — a deliberately conservative default
    that still prevents BUYs from firing on low-confidence regime data.
    """
    close = nifty_df["close"]
    dma_50 = sma(close, 50)
    dma_200 = sma(close, 200)
    dma_50_rising = dma_50.diff() > 0

    risk_on = (close > dma_50) & (close > dma_200) & dma_50_rising
    risk_off = close < dma_200
    # Caution is anything else (between the DMAs, or 50-DMA flat/falling)

    states = pd.Series(Regime.CAUTION, index=close.index, dtype=object)
    states[risk_off.fillna(False)] = Regime.RISK_OFF
    states[risk_on.fillna(False)] = Regime.RISK_ON
    # Bars where 200-DMA is undefined fall through to CAUTION
    return states


def latest_regime(nifty_df: pd.DataFrame) -> Regime:
    """Convenience: regime of the most recent bar."""
    return Regime(market_regime(nifty_df).iloc[-1])
