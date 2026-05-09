"""Realized volatility and jump-volatility helpers."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats


EXPECTED_5M_BARS_PER_DAY = 288
MU_1 = math.sqrt(2.0 / math.pi)


def add_intraday_returns(klines: pd.DataFrame) -> pd.DataFrame:
    """Add per-candle log returns using close/open within each 5-minute bar."""

    required = {"symbol", "open_datetime", "open", "close"}
    missing = required - set(klines.columns)
    if missing:
        raise ValueError(f"Missing kline columns: {sorted(missing)}")

    frame = klines.copy()
    frame["date"] = frame["open_datetime"].dt.date
    frame["intraday_return"] = np.log(frame["close"].astype(float) / frame["open"].astype(float))
    return frame


def threshold_bipower_variation(
    returns: np.ndarray | pd.Series,
    *,
    threshold_multiplier: float = 4.0,
) -> float:
    """Compute a compact TBPV-style continuous variation estimator.

    The threshold is daily and variance-scaled. It is deliberately simple and
    transparent so the Table 7 robustness calculation is auditable.
    """

    values = np.asarray(returns, dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 2:
        return 0.0

    rv = float(np.sum(values**2))
    if rv <= 0.0:
        return 0.0

    threshold = (threshold_multiplier**2) * (rv / values.size)
    keep = (values[1:] ** 2 <= threshold) & (values[:-1] ** 2 <= threshold)
    tbpv = float((1.0 / MU_1**2) * np.sum(np.abs(values[1:]) * np.abs(values[:-1]) * keep))
    return max(0.0, min(tbpv, rv))


def daily_volatility_metrics(klines: pd.DataFrame) -> pd.DataFrame:
    """Compute daily RV, CV, and JV for complete 5-minute UTC days."""

    returns = add_intraday_returns(klines)
    rows: list[dict[str, object]] = []

    for (symbol, day), group in returns.groupby(["symbol", "date"], sort=True):
        count = int(group["intraday_return"].count())
        complete = count == EXPECTED_5M_BARS_PER_DAY
        if not complete:
            continue

        intraday = group["intraday_return"].to_numpy(dtype=float)
        rv = float(np.sum(intraday**2))
        cv = threshold_bipower_variation(intraday)
        rows.append(
            {
                "symbol": symbol,
                "date": pd.Timestamp(day),
                "bar_count": count,
                "rv": rv,
                "cv": cv,
                "jv": max(rv - cv, 0.0),
            }
        )

    return pd.DataFrame(rows)


def daily_close_returns(klines: pd.DataFrame) -> pd.DataFrame:
    """Build daily close-to-close returns from 5-minute klines."""

    frame = klines.copy()
    frame["date"] = frame["open_datetime"].dt.date
    closes = (
        frame.sort_values(["symbol", "open_datetime"])
        .groupby(["symbol", "date"], as_index=False)
        .tail(1)[["symbol", "date", "close"]]
        .sort_values(["symbol", "date"])
    )
    closes["daily_return"] = closes.groupby("symbol")["close"].transform(lambda s: np.log(s.astype(float) / s.astype(float).shift(1)))
    panel = closes.pivot(index="date", columns="symbol", values="daily_return")
    panel.index = pd.to_datetime(panel.index)
    return panel.dropna(how="any")


def pre_post_mean_test(values: pd.DataFrame, break_date: pd.Timestamp, value_col: str) -> tuple[float, float, float, float]:
    """Return pre mean, post mean, delta, and Welch t-test p-value."""

    pre = values.loc[values["date"] < break_date, value_col].dropna()
    post = values.loc[values["date"] >= break_date, value_col].dropna()
    pre_mean = float(pre.mean()) if not pre.empty else float("nan")
    post_mean = float(post.mean()) if not post.empty else float("nan")
    delta = post_mean - pre_mean
    if len(pre) < 2 or len(post) < 2:
        p_value = float("nan")
    else:
        p_value = float(stats.ttest_ind(post, pre, equal_var=False, nan_policy="omit").pvalue)
    return pre_mean, post_mean, delta, p_value

