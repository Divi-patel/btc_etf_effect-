#!/usr/bin/env python3
"""Fetch daily BTC, ETH, VIX from yfinance for the BEKK QMLE rebuild.

Mirrors the lab R code's `prepare_data()` (varx_garch_bekk.R:17-65) which
calls quantmod::getSymbols("BTC-USD", "ETH-USD", "^VIX") from Yahoo Finance.

Output: data/interim/yfinance_daily.parquet with columns
    date, btc_close, eth_close, vix_close
covering 2022-06-01 (paper window start) through 2024-12-31.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf

from btc_eth_research.config import INTERIM_DATA_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2022-06-01")
    parser.add_argument("--end", default="2025-01-01", help="exclusive end date")
    parser.add_argument(
        "--output",
        type=Path,
        default=INTERIM_DATA_DIR / "yfinance_daily.parquet",
    )
    return parser.parse_args()


def _close_series(ticker: str, start: str, end: str, name: str) -> pd.Series:
    """Pull a single ticker's adjusted close as a tidy Series."""
    raw = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    if raw.empty:
        raise SystemExit(f"yfinance returned empty data for {ticker}")
    series = raw["Close"].rename(name)
    series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
    series = series[~series.index.duplicated(keep="last")]
    return series


def main() -> None:
    args = parse_args()

    btc = _close_series("BTC-USD", args.start, args.end, "btc_close")
    eth = _close_series("ETH-USD", args.start, args.end, "eth_close")
    vix = _close_series("^VIX", args.start, args.end, "vix_close")

    crypto_dates = btc.index.union(eth.index).sort_values()
    panel = pd.DataFrame(index=crypto_dates)
    panel["btc_close"] = btc
    panel["eth_close"] = eth
    panel["vix_close"] = vix.reindex(crypto_dates).ffill()

    panel = panel.dropna(subset=["btc_close", "eth_close"]).copy()
    panel.index.name = "date"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.output)

    print(f"wrote {args.output}")
    print(f"rows: {len(panel)}")
    print(f"date range: {panel.index.min().date()} to {panel.index.max().date()}")
    print(f"columns: {list(panel.columns)}")
    print(f"NA counts: {panel.isna().sum().to_dict()}")


if __name__ == "__main__":
    main()
