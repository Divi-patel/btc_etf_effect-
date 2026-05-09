from btc_eth_research.binance import KLINE_COLUMNS, iter_months, parse_kline_csv


def test_iter_months_is_inclusive():
    assert iter_months("2023-08", "2023-10") == ["2023-08", "2023-09", "2023-10"]


def test_parse_binance_kline_csv_types_rows():
    row = ",".join(
        [
            "1690848000000",
            "29182.10000000",
            "29200.00000000",
            "29100.00000000",
            "29150.00000000",
            "12.5",
            "1690848299999",
            "364375.0",
            "123",
            "4.2",
            "122430.0",
            "0",
        ]
    )
    frame = parse_kline_csv((row + "\n").encode(), symbol="BTCUSDT")
    assert list(frame.columns[: len(KLINE_COLUMNS)]) == KLINE_COLUMNS
    assert frame.loc[0, "symbol"] == "BTCUSDT"
    assert frame.loc[0, "close"] == 29150.0
    assert str(frame.loc[0, "open_datetime"]) == "2023-08-01 00:00:00+00:00"

