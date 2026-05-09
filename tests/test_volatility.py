import numpy as np
import pandas as pd

from btc_eth_research.volatility import daily_volatility_metrics, threshold_bipower_variation


def _one_day_klines(symbol: str, returns: np.ndarray) -> pd.DataFrame:
    timestamps = pd.date_range("2023-10-01", periods=288, freq="5min", tz="UTC")
    rows = []
    price = 100.0
    for ts, ret in zip(timestamps, returns):
        open_price = price
        close_price = open_price * float(np.exp(ret))
        rows.append(
            {
                "symbol": symbol,
                "open_datetime": ts,
                "open": open_price,
                "high": max(open_price, close_price),
                "low": min(open_price, close_price),
                "close": close_price,
                "volume": 1.0,
            }
        )
        price = close_price
    return pd.DataFrame(rows)


def test_constant_price_has_zero_volatility():
    frame = _one_day_klines("BTCUSDT", np.zeros(288))
    metrics = daily_volatility_metrics(frame)
    assert metrics.loc[0, "rv"] == 0.0
    assert metrics.loc[0, "cv"] == 0.0
    assert metrics.loc[0, "jv"] == 0.0


def test_injected_jump_creates_positive_jump_variation():
    returns = np.zeros(288)
    returns[100] = 0.10
    frame = _one_day_klines("BTCUSDT", returns)
    metrics = daily_volatility_metrics(frame)
    assert metrics.loc[0, "rv"] > 0.0
    assert metrics.loc[0, "jv"] > 0.0


def test_incomplete_day_is_excluded():
    frame = _one_day_klines("BTCUSDT", np.zeros(288)).iloc[:-1]
    metrics = daily_volatility_metrics(frame)
    assert metrics.empty


def test_tbpv_is_bounded_by_rv():
    returns = np.array([0.001, -0.002, 0.003, -0.001])
    rv = float(np.sum(returns**2))
    assert 0.0 <= threshold_bipower_variation(returns) <= rv

