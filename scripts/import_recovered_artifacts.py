#!/usr/bin/env python3
"""Import panels from the cloned legacy repo under lab/."""

from __future__ import annotations

from btc_eth_research.recovered import LEGACY_REPO_DIR, legacy_repo_available, write_recovered_interim


def main() -> None:
    if not legacy_repo_available():
        raise SystemExit(f"Missing legacy repo: {LEGACY_REPO_DIR}")
    returns_path, volatility_path = write_recovered_interim()
    print(f"wrote {returns_path}")
    print(f"wrote {volatility_path}")


if __name__ == "__main__":
    main()

