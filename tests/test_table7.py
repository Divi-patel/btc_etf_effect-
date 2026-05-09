import pandas as pd
import pytest

from btc_eth_research.table7 import TABLE7_COLUMNS, render_table7_markdown, validate_table7_schema


def test_validate_table7_schema_rejects_missing_columns():
    with pytest.raises(ValueError):
        validate_table7_schema(pd.DataFrame({"break_date": ["2023-10-23"]}))


def test_render_table7_markdown_contains_required_headers():
    row = {column: 0.0 for column in TABLE7_COLUMNS}
    row.update(
        {
            "break_date": "2023-10-23",
            "event": "baseline",
            "jv_label": "Strong decrease",
            "short_run_label": "Strong short-run spillover decrease",
            "long_run_label": "Strong long-run spillover increase",
        }
    )
    markdown = render_table7_markdown(pd.DataFrame([row]))
    assert "Table 7. Robustness Test" in markdown
    assert "Delta Jump Volatility" in markdown
    assert "Delta Short-run Spillover" in markdown
    assert "Delta Long-run Spillover" in markdown

