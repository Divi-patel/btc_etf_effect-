"""Daily panel loader for the BEKK pipeline.

Loads the yfinance daily parquet, computes log returns, lags VIX, and
constructs the break dummy. Mirrors the R code's prepare_data() in
varx_garch_bekk.R:17-65.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import INTERIM_DATA_DIR


DEFAULT_PANEL = INTERIM_DATA_DIR / "yfinance_daily.parquet"


def load_aligned_panel(
    break_date: date | pd.Timestamp,
    *,
    start: str = "2022-06-01",
    end: str = "2024-12-31",
    panel_path: Path = DEFAULT_PANEL,
) -> pd.DataFrame:
    """Return a DataFrame ready to feed the VAR-X stage.

    Columns:
        btc_return    log return of BTC
        eth_return    log return of ETH
        vix_lag       lagged VIX level
        break_dummy   1 if date >= break_date else 0

    The first row is dropped because differencing produces NaN there.
    Rows after lag 1 application have valid vix_lag.
    """
    if not panel_path.exists():
        raise FileNotFoundError(
            f"Daily panel not found at {panel_path}. "
            "Run scripts/fetch_yfinance_daily.py first."
        )

    panel = pd.read_parquet(panel_path)
    panel.index = pd.to_datetime(panel.index)
    panel = panel.loc[start:end].copy()

    panel["btc_return"] = np.log(panel["btc_close"]).diff()
    panel["eth_return"] = np.log(panel["eth_close"]).diff()
    panel["vix_lag"] = panel["vix_close"].shift(1)
    break_ts = pd.Timestamp(break_date)
    panel["break_dummy"] = (panel.index >= break_ts).astype(int)

    out = panel[["btc_return", "eth_return", "vix_lag", "break_dummy"]].dropna()
    return out
