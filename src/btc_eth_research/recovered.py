"""Load artifacts recovered from the cloned legacy research repository."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from btc_eth_research.config import INTERIM_DATA_DIR, PROJECT_ROOT


LEGACY_REPO_DIR = PROJECT_ROOT / "lab" / "Crypto-ETF-effect-and-Volatility-Modeling"
LEGACY_SUMMARY_DIR = LEGACY_REPO_DIR / "1_data_statistical_summary"
LEGACY_HF_DIR = LEGACY_REPO_DIR / "3_high_frequency_data_analysis"
LEGACY_MODEL_DIR = LEGACY_REPO_DIR / "4_VAR-X-GARCH-BEKK_for_btc_eth"


def legacy_repo_available() -> bool:
    return LEGACY_REPO_DIR.exists()


def load_recovered_returns() -> pd.DataFrame:
    """Load BTC/ETH daily returns from recovered legacy CSVs."""

    btc = pd.read_csv(LEGACY_SUMMARY_DIR / "BTC_data.csv", parse_dates=["Date"])
    eth = pd.read_csv(LEGACY_SUMMARY_DIR / "ETH_data.csv", parse_dates=["Date"])

    btc_returns = btc[["Date", "Returns"]].rename(columns={"Returns": "BTCUSDT"}).set_index("Date")
    eth_returns = eth[["Date", "Returns"]].rename(columns={"Returns": "ETHUSDT"}).set_index("Date")
    returns = btc_returns.join(eth_returns, how="inner").sort_index()
    returns.index = pd.to_datetime(returns.index)
    return returns.dropna(how="any")


def load_recovered_volatility() -> pd.DataFrame:
    """Load precomputed BTC/ETH daily RV/CV/JV panels from recovered CSVs."""

    btc = pd.read_csv(LEGACY_HF_DIR / "btc_volatility_measures_185.csv", parse_dates=["Date"])
    eth = pd.read_csv(LEGACY_HF_DIR / "ETH_volatility_measures_185.csv", parse_dates=["Date"])
    btc["symbol"] = "BTCUSDT"
    eth["symbol"] = "ETHUSDT"
    frame = pd.concat([btc, eth], ignore_index=True)
    frame = frame.rename(columns={"Date": "date", "RV": "rv", "CV": "cv", "JV": "jv"})
    frame["date"] = pd.to_datetime(frame["date"])
    return frame[["symbol", "date", "rv", "cv", "jv"]].sort_values(["symbol", "date"]).reset_index(drop=True)


def write_recovered_interim(interim_dir: Path = INTERIM_DATA_DIR) -> tuple[Path, Path]:
    """Materialize recovered daily panels into ignored interim parquet files."""

    interim_dir.mkdir(parents=True, exist_ok=True)
    returns_path = interim_dir / "recovered_daily_returns.parquet"
    volatility_path = interim_dir / "recovered_daily_volatility.parquet"
    load_recovered_returns().to_parquet(returns_path)
    load_recovered_volatility().to_parquet(volatility_path, index=False)
    return returns_path, volatility_path

