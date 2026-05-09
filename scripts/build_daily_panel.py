#!/usr/bin/env python3
"""Build daily volatility and close-return panels from kline parquet data."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from btc_eth_research.config import INTERIM_DATA_DIR
from btc_eth_research.volatility import daily_close_returns, daily_volatility_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INTERIM_DATA_DIR / "binance_klines_5m.parquet")
    parser.add_argument("--vol-output", type=Path, default=INTERIM_DATA_DIR / "daily_volatility.parquet")
    parser.add_argument("--returns-output", type=Path, default=INTERIM_DATA_DIR / "daily_returns.parquet")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    klines = pd.read_parquet(args.input)
    klines["open_datetime"] = pd.to_datetime(klines["open_datetime"], utc=True)
    volatility = daily_volatility_metrics(klines)
    returns = daily_close_returns(klines)

    args.vol_output.parent.mkdir(parents=True, exist_ok=True)
    volatility.to_parquet(args.vol_output, index=False)
    returns.to_parquet(args.returns_output)
    print(f"wrote {args.vol_output} rows={len(volatility)}")
    print(f"wrote {args.returns_output} rows={len(returns)}")


if __name__ == "__main__":
    main()

