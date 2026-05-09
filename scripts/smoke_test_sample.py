#!/usr/bin/env python3
"""Run the Table 7 pipeline on deterministic synthetic data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from btc_eth_research.table7 import generate_table7_results, write_table7_outputs


def synthetic_klines() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    timestamps = pd.date_range("2023-08-01", "2024-02-15 23:55:00", freq="5min", tz="UTC")
    rows = []
    for symbol, start_price, drift in [("BTCUSDT", 30000.0, 0.000002), ("ETHUSDT", 1800.0, 0.000001)]:
        price = start_price
        for ts in timestamps:
            shock_scale = 0.0015 if ts.date() < pd.Timestamp("2023-10-23").date() else 0.0008
            open_price = price
            ret = drift + rng.normal(0.0, shock_scale)
            if ts == pd.Timestamp("2023-09-10 12:00:00", tz="UTC"):
                ret += 0.08
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


def main() -> None:
    output_root = Path("/private/tmp/btc_eth_table7_smoke")
    results = generate_table7_results(synthetic_klines())
    write_table7_outputs(results, output_root / "processed", output_root / "tables")
    print(f"wrote smoke outputs under {output_root}")


if __name__ == "__main__":
    main()

