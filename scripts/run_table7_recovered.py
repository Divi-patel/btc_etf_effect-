#!/usr/bin/env python3
"""Generate Table 7 using the cloned legacy repo's recovered daily panels."""

from __future__ import annotations

from btc_eth_research.config import PROCESSED_DATA_DIR, TABLES_DIR
from btc_eth_research.recovered import legacy_repo_available, load_recovered_returns, load_recovered_volatility
from btc_eth_research.table7 import generate_table7_from_panels, write_table7_outputs


def main() -> None:
    if not legacy_repo_available():
        raise SystemExit("Clone the legacy repo into lab/Crypto-ETF-effect-and-Volatility-Modeling first.")

    results = generate_table7_from_panels(
        volatility=load_recovered_volatility(),
        returns=load_recovered_returns(),
    )
    write_table7_outputs(results, PROCESSED_DATA_DIR, TABLES_DIR)
    print(f"wrote {PROCESSED_DATA_DIR / 'table7_results.csv'}")
    print(f"wrote {TABLES_DIR / 'table7.md'}")
    print(f"wrote {TABLES_DIR / 'table7_analysis.md'}")


if __name__ == "__main__":
    main()

