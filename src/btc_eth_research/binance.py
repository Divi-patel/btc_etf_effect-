"""Binance public kline download and parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import requests


KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
]


@dataclass(frozen=True)
class BinanceMonthlyFile:
    symbol: str
    interval: str
    month: str

    @property
    def filename(self) -> str:
        return f"{self.symbol}-{self.interval}-{self.month}.zip"

    @property
    def url(self) -> str:
        return (
            "https://data.binance.vision/data/spot/monthly/klines/"
            f"{self.symbol}/{self.interval}/{self.filename}"
        )


def iter_months(start_month: str, end_month: str) -> list[str]:
    """Return inclusive YYYY-MM month labels."""

    start = pd.Period(start_month, freq="M")
    end = pd.Period(end_month, freq="M")
    if end < start:
        raise ValueError("end_month must be on or after start_month")
    return [str(period) for period in pd.period_range(start, end, freq="M")]


def parse_kline_csv(csv_bytes: bytes, symbol: str) -> pd.DataFrame:
    """Parse a Binance kline CSV payload into typed rows."""

    frame = pd.read_csv(BytesIO(csv_bytes), header=None, names=KLINE_COLUMNS)
    frame = frame.dropna(how="all")
    frame["symbol"] = symbol

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_asset_volume",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    integer_columns = ["open_time", "close_time", "number_of_trades"]
    for column in integer_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")

    frame["open_datetime"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    frame["close_datetime"] = pd.to_datetime(frame["close_time"], unit="ms", utc=True)
    return frame


def parse_kline_zip(zip_bytes: bytes, symbol: str) -> pd.DataFrame:
    """Parse the first CSV file inside a Binance monthly kline ZIP."""

    with ZipFile(BytesIO(zip_bytes)) as archive:
        csv_names = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csv_names:
            raise ValueError("Binance ZIP did not contain a CSV file")
        return parse_kline_csv(archive.read(csv_names[0]), symbol=symbol)


def download_monthly_zip(
    monthly_file: BinanceMonthlyFile,
    raw_dir: Path,
    *,
    timeout: int = 60,
    force: bool = False,
) -> Path:
    """Download one Binance monthly kline ZIP if it is not already present."""

    target_dir = raw_dir / "binance" / "spot" / "monthly" / "klines" / monthly_file.symbol / monthly_file.interval
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / monthly_file.filename
    if target.exists() and not force:
        return target

    response = requests.get(monthly_file.url, timeout=timeout)
    response.raise_for_status()
    target.write_bytes(response.content)
    return target


def load_monthly_zip(path: Path, symbol: str) -> pd.DataFrame:
    """Load a previously downloaded Binance monthly kline ZIP."""

    return parse_kline_zip(path.read_bytes(), symbol=symbol)


def fetch_monthly_klines(
    symbols: list[str],
    interval: str,
    start_month: str,
    end_month: str,
    raw_dir: Path,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """Download and combine Binance monthly kline data."""

    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        for month in iter_months(start_month, end_month):
            monthly_file = BinanceMonthlyFile(symbol=symbol, interval=interval, month=month)
            path = download_monthly_zip(monthly_file, raw_dir=raw_dir, force=force)
            frames.append(load_monthly_zip(path, symbol=symbol))

    if not frames:
        raise ValueError("No kline frames were loaded")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["symbol", "open_datetime"]).reset_index(drop=True)
    return combined


def clip_klines(frame: pd.DataFrame, start: datetime | None, end: datetime | None) -> pd.DataFrame:
    """Clip klines by inclusive UTC datetimes."""

    clipped = frame
    if start is not None:
        clipped = clipped[clipped["open_datetime"] >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        clipped = clipped[clipped["open_datetime"] <= pd.Timestamp(end, tz="UTC")]
    return clipped.reset_index(drop=True)

