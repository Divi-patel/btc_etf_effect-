"""Generate the Table 7 robustness outputs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from btc_eth_research.config import BREAK_DATES
from btc_eth_research.spillover import directional_label, estimate_spillover_shifts
from btc_eth_research.varx import estimate_varx_residuals
from btc_eth_research.volatility import daily_close_returns, daily_volatility_metrics, pre_post_mean_test


TABLE7_COLUMNS = [
    "break_date",
    "event",
    "btc_jv_pre_mean",
    "btc_jv_post_mean",
    "btc_jv_delta",
    "btc_jv_p",
    "eth_jv_pre_mean",
    "eth_jv_post_mean",
    "eth_jv_delta",
    "eth_jv_p",
    "mean_jv_delta",
    "jv_label",
    "a12_star",
    "a12_p",
    "a21_star",
    "a21_p",
    "short_run_label",
    "g12_star",
    "g12_p",
    "g21_star",
    "g21_p",
    "long_run_label",
]


def _fmt(value: float, digits: int = 4) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def _label_jump_delta(btc_delta: float, btc_p: float, eth_delta: float, eth_p: float) -> str:
    deltas = [btc_delta, eth_delta]
    p_values = [btc_p, eth_p]
    if all(np.isfinite(delta) and delta < 0 for delta in deltas) and all(np.isfinite(p) and p <= 0.05 for p in p_values):
        return "Strong decrease"
    if all(np.isfinite(delta) and delta < 0 for delta in deltas) and any(np.isfinite(p) and p <= 0.10 for p in p_values):
        return "Moderate decrease"
    if np.nanmean(deltas) < 0:
        return "Weak decrease"
    return "No robust decrease"


def generate_table7_from_panels(volatility: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    """Generate numeric robustness results from daily volatility and return panels."""
    rows: list[dict[str, object]] = []

    for item in BREAK_DATES:
        break_ts = pd.Timestamp(item.break_date)
        btc_vol = volatility[volatility["symbol"] == "BTCUSDT"]
        eth_vol = volatility[volatility["symbol"] == "ETHUSDT"]

        btc_pre, btc_post, btc_delta, btc_p = pre_post_mean_test(btc_vol, break_ts, "jv")
        eth_pre, eth_post, eth_delta, eth_p = pre_post_mean_test(eth_vol, break_ts, "jv")

        residuals = estimate_varx_residuals(returns, break_ts)
        spillovers = estimate_spillover_shifts(residuals, break_ts)

        short_run_label = directional_label(
            [spillovers["a12_star"], spillovers["a21_star"]],
            [spillovers["a12_p"], spillovers["a21_p"]],
            expected_sign=-1,
            noun="short-run spillover decrease",
        )
        long_run_label = directional_label(
            [spillovers["g12_star"], spillovers["g21_star"]],
            [spillovers["g12_p"], spillovers["g21_p"]],
            expected_sign=1,
            noun="long-run spillover increase",
        )

        rows.append(
            {
                "break_date": item.break_date.isoformat(),
                "event": item.label,
                "btc_jv_pre_mean": btc_pre,
                "btc_jv_post_mean": btc_post,
                "btc_jv_delta": btc_delta,
                "btc_jv_p": btc_p,
                "eth_jv_pre_mean": eth_pre,
                "eth_jv_post_mean": eth_post,
                "eth_jv_delta": eth_delta,
                "eth_jv_p": eth_p,
                "mean_jv_delta": float(np.nanmean([btc_delta, eth_delta])),
                "jv_label": _label_jump_delta(btc_delta, btc_p, eth_delta, eth_p),
                **spillovers,
                "short_run_label": short_run_label,
                "long_run_label": long_run_label,
            }
        )

    return pd.DataFrame(rows, columns=TABLE7_COLUMNS)


def generate_table7_results(klines: pd.DataFrame) -> pd.DataFrame:
    """Generate numeric robustness results from raw 5-minute klines."""

    volatility = daily_volatility_metrics(klines)
    returns = daily_close_returns(klines)
    return generate_table7_from_panels(volatility, returns)


def validate_table7_schema(results: pd.DataFrame) -> None:
    """Raise if Table 7 results are missing required columns."""

    missing = [column for column in TABLE7_COLUMNS if column not in results.columns]
    if missing:
        raise ValueError(f"Table 7 results missing columns: {missing}")


def render_table7_markdown(results: pd.DataFrame) -> str:
    """Render paper-ready Table 7 Markdown."""

    validate_table7_schema(results)
    table = results.copy()
    table["Date"] = table["break_date"]
    table["Event"] = table["event"]
    table["Delta Jump Volatility"] = table.apply(
        lambda row: (
            f"{row['jv_label']} "
            f"(BTC Δ={_fmt(row['btc_jv_delta'])}, p={_fmt(row['btc_jv_p'], 3)}; "
            f"ETH Δ={_fmt(row['eth_jv_delta'])}, p={_fmt(row['eth_jv_p'], 3)})"
        ),
        axis=1,
    )
    table["Delta Short-run Spillover"] = table.apply(
        lambda row: (
            f"{row['short_run_label']} "
            f"(a12*={_fmt(row['a12_star'])}, p={_fmt(row['a12_p'], 3)}; "
            f"a21*={_fmt(row['a21_star'])}, p={_fmt(row['a21_p'], 3)})"
        ),
        axis=1,
    )
    table["Delta Long-run Spillover"] = table.apply(
        lambda row: (
            f"{row['long_run_label']} "
            f"(g12*={_fmt(row['g12_star'])}, p={_fmt(row['g12_p'], 3)}; "
            f"g21*={_fmt(row['g21_star'])}, p={_fmt(row['g21_p'], 3)})"
        ),
        axis=1,
    )

    columns = [
        "Date",
        "Event",
        "Delta Jump Volatility",
        "Delta Short-run Spillover",
        "Delta Long-run Spillover",
    ]
    note = (
        "\n\n"
        "Note: Jump-volatility deltas are computed from recovered daily RV/CV/JV panels. "
        "Spillover deltas are BEKK-style proxy estimates from VAR-X residual shocks and "
        "lagged volatility terms; regenerate this table if the full recovered R QMLE BEKK "
        "estimator is ported or run in an R environment.\n"
    )
    return "# Table 7. Robustness Test: Structural Break Comparison Across Alternative ETF Dates\n\n" + table[columns].to_markdown(index=False) + note


def render_table7_analysis(results: pd.DataFrame) -> str:
    """Render a short interpretation note for generated Table 7 results."""

    validate_table7_schema(results)
    ranked = results.copy()
    ranked["baseline_score"] = 0.0
    ranked["baseline_score"] += np.where(ranked["mean_jv_delta"] < 0, np.abs(ranked["mean_jv_delta"]), 0.0)
    ranked["baseline_score"] += np.where((ranked["a12_star"] < 0) & (ranked["a21_star"] < 0), 1.0, 0.0)
    ranked["baseline_score"] += np.where((ranked["g12_star"] > 0) & (ranked["g21_star"] > 0), 1.0, 0.0)
    strongest = ranked.sort_values("baseline_score", ascending=False).iloc[0]

    lines = [
        "# Table 7 Analysis",
        "",
        f"The strongest candidate break date under the current reproducible pipeline is `{strongest['break_date']}` ({strongest['event']}).",
        "",
        "Interpretation:",
        "",
    ]
    for _, row in results.iterrows():
        lines.append(
            "- "
            f"`{row['break_date']}`: {row['jv_label']}; "
            f"{row['short_run_label']}; {row['long_run_label']}."
        )
    lines.extend(
        [
            "",
            "Method note: spillover coefficients are BEKK-style OLS proxies for short-run shock shifts and long-run volatility-persistence shifts. "
            "If a full BEKK maximum-likelihood implementation is later recovered or added, this output should be regenerated with that estimator.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_table7_outputs(results: pd.DataFrame, processed_dir: Path, tables_dir: Path) -> None:
    """Write CSV and Markdown Table 7 artifacts."""

    validate_table7_schema(results)
    processed_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(processed_dir / "table7_results.csv", index=False)
    (tables_dir / "table7.md").write_text(render_table7_markdown(results), encoding="utf-8")
    (tables_dir / "table7_analysis.md").write_text(render_table7_analysis(results), encoding="utf-8")


def replace_table7_in_paper(paper_path: Path, table_markdown: str) -> bool:
    """Replace the placeholder Table 7 block in the converted paper Markdown."""

    text = paper_path.read_text(encoding="utf-8")
    start = text.find("**Table 7. Robustness Test:")
    end = text.find("**Figure 5.", start)
    if start == -1 or end == -1:
        return False
    replacement = table_markdown.replace("# Table 7.", "**Table 7.").replace("\n\n|", "**\n\n|", 1)
    paper_path.write_text(text[:start] + replacement + "\n" + text[end:], encoding="utf-8")
    return True
