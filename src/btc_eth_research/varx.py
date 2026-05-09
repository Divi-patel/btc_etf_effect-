"""VAR-X residual estimation used before spillover analysis."""

from __future__ import annotations

import pandas as pd
import statsmodels.api as sm


def estimate_varx_residuals(
    returns: pd.DataFrame,
    break_date: pd.Timestamp,
    *,
    btc_col: str = "BTCUSDT",
    eth_col: str = "ETHUSDT",
    exogenous: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Estimate two OLS VAR-X equations and return residuals.

    The baseline design uses lagged BTC/ETH returns and a post-break dummy.
    Optional exogenous columns, such as lagged VIX, can be joined by date.
    """

    required = {btc_col, eth_col}
    missing = required - set(returns.columns)
    if missing:
        raise ValueError(f"Missing return columns: {sorted(missing)}")

    frame = returns[[btc_col, eth_col]].copy().dropna()
    frame.index = pd.to_datetime(frame.index)
    frame["btc_lag1"] = frame[btc_col].shift(1)
    frame["eth_lag1"] = frame[eth_col].shift(1)
    frame["post_break"] = (frame.index >= break_date).astype(int)

    if exogenous is not None and not exogenous.empty:
        extra = exogenous.copy()
        extra.index = pd.to_datetime(extra.index)
        frame = frame.join(extra, how="left")

    frame = frame.dropna()
    if len(frame) < 10:
        raise ValueError("Not enough observations to estimate VAR-X residuals")

    regressors = ["btc_lag1", "eth_lag1", "post_break"]
    if exogenous is not None and not exogenous.empty:
        regressors.extend(list(exogenous.columns))

    x = sm.add_constant(frame[regressors], has_constant="add")
    btc_model = sm.OLS(frame[btc_col], x).fit(cov_type="HC3")
    eth_model = sm.OLS(frame[eth_col], x).fit(cov_type="HC3")

    return pd.DataFrame(
        {
            "btc_resid": btc_model.resid,
            "eth_resid": eth_model.resid,
        },
        index=frame.index,
    )

