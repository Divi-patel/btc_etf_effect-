#!/usr/bin/env python3
"""Generate Table 7 outputs from an interim kline parquet file."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from btc_eth_research.config import DOCS_DIR, INTERIM_DATA_DIR, PROCESSED_DATA_DIR, TABLES_DIR
from btc_eth_research.table7 import (
    generate_table7_from_panels,
    generate_table7_results,
    render_table7_markdown,
    replace_table7_in_paper,
    write_table7_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INTERIM_DATA_DIR / "binance_klines_5m.parquet")
    parser.add_argument("--returns-input", type=Path, default=None)
    parser.add_argument("--volatility-input", type=Path, default=None)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DATA_DIR)
    parser.add_argument("--tables-dir", type=Path, default=TABLES_DIR)
    parser.add_argument("--update-paper", action="store_true", help="Replace the Table 7 placeholder in docs/main_paper.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.returns_input and args.volatility_input:
        returns = pd.read_parquet(args.returns_input)
        returns.index = pd.to_datetime(returns.index)
        volatility = pd.read_parquet(args.volatility_input)
        volatility["date"] = pd.to_datetime(volatility["date"])
        results = generate_table7_from_panels(volatility, returns)
    else:
        if not args.input.exists():
            raise SystemExit(
                f"Missing input parquet: {args.input}. Run scripts/fetch_binance_klines.py first, "
                "or pass --returns-input and --volatility-input for recovered panels."
            )
        klines = pd.read_parquet(args.input)
        klines["open_datetime"] = pd.to_datetime(klines["open_datetime"], utc=True)
        results = generate_table7_results(klines)
    write_table7_outputs(results, args.processed_dir, args.tables_dir)
    print(f"wrote {args.processed_dir / 'table7_results.csv'}")
    print(f"wrote {args.tables_dir / 'table7.md'}")
    print(f"wrote {args.tables_dir / 'table7_analysis.md'}")

    if args.update_paper:
        paper_path = DOCS_DIR / "main_paper.md"
        updated = replace_table7_in_paper(paper_path, render_table7_markdown(results))
        if not updated:
            raise SystemExit("Could not find Table 7 placeholder block in docs/main_paper.md")
        print(f"updated {paper_path}")


if __name__ == "__main__":
    main()
