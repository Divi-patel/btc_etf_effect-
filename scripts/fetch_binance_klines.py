#!/usr/bin/env python3
"""Download Binance public 5-minute klines for Table 7."""

from __future__ import annotations

import argparse
from pathlib import Path

from btc_eth_research.binance import fetch_monthly_klines
from btc_eth_research.config import (
    DEFAULT_END_MONTH,
    DEFAULT_INTERVAL,
    DEFAULT_START_MONTH,
    DEFAULT_SYMBOLS,
    INTERIM_DATA_DIR,
    RAW_DATA_DIR,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--interval", default=DEFAULT_INTERVAL)
    parser.add_argument("--start", default=DEFAULT_START_MONTH, help="Inclusive YYYY-MM start month")
    parser.add_argument("--end", default=DEFAULT_END_MONTH, help="Inclusive YYYY-MM end month")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--output", type=Path, default=INTERIM_DATA_DIR / "binance_klines_5m.parquet")
    parser.add_argument("--force", action="store_true", help="Re-download existing ZIP files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = fetch_monthly_klines(
        symbols=args.symbols,
        interval=args.interval,
        start_month=args.start,
        end_month=args.end,
        raw_dir=args.raw_dir,
        force=args.force,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.output, index=False)
    print(f"wrote {args.output} rows={len(frame)} symbols={','.join(args.symbols)}")


if __name__ == "__main__":
    main()

