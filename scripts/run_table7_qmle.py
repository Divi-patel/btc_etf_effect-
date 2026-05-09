#!/usr/bin/env python3
"""Generate Table 7 (real QMLE BEKK at three break dates).

Runs the full Python BEKK port at:
    2023-08-29 (Grayscale court ruling)
    2023-10-23 (paper headline date)
    2024-01-10 (SEC official approval)

Writes:
    data/processed/table7_qmle_results.csv  — wide table of params, SEs, p-values, diag
    docs/tables/table7_qmle.md              — human-readable Table 7 (markdown)
    docs/tables/table7_qmle_analysis.md     — narrative comparing the three dates

This replaces the OLS-proxy `scripts/run_table7.py` with a real QMLE estimator.
The proxy script is left in place; both can co-exist.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from btc_eth_research.bekk.fit import fit_bekk, render_param_table
from btc_eth_research.config import (
    BREAK_DATES,
    DOCS_DIR,
    PROCESSED_DATA_DIR,
    TABLES_DIR,
)


HEADLINE_PARAMS = ("a12_star", "a21_star", "g12_star", "g21_star")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--processed-dir", type=Path, default=PROCESSED_DATA_DIR)
    p.add_argument("--tables-dir", type=Path, default=TABLES_DIR)
    p.add_argument("--grid-points", type=int, default=5)
    p.add_argument("--max-iter", type=int, default=10000)
    return p.parse_args()


def _format_param(est: float, p_val: float) -> str:
    stars = "***" if p_val < 0.01 else ("**" if p_val < 0.05 else ("*" if p_val < 0.10 else ""))
    return f"{est:+.4f}{stars}"


def main() -> None:
    args = parse_args()
    args.processed_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    summaries: list[dict] = []

    for spec in BREAK_DATES:
        print()
        print("=" * 70)
        print(f"Fitting BEKK QMLE: break = {spec.break_date} ({spec.label})")
        print("=" * 70)
        result = fit_bekk(
            spec.break_date,
            grid_points=args.grid_points,
            max_iter=args.max_iter,
            verbose=True,
        )

        param_df = render_param_table(result)
        wide = {
            "break_date": str(spec.break_date),
            "event": spec.label,
            "n_obs": result.n_obs,
            "log_likelihood": -result.optim.nll,
            "aic": result.diagnostics.aic,
            "bic": result.diagnostics.bic,
            "persistence_pre": result.diagnostics.persistence,
            "persistence_post": result.diagnostics.persistence_post_break,
            "ljung_box_z2_btc_p": result.diagnostics.ljung_box_z2["BTC"][1],
            "ljung_box_z2_eth_p": result.diagnostics.ljung_box_z2["ETH"][1],
            "optim_success": result.optim.success,
            "optim_iter": result.optim.nit,
        }
        for _, row in param_df.iterrows():
            wide[f"{row['param']}_est"] = row["est"]
            wide[f"{row['param']}_se"] = row["se"]
            wide[f"{row['param']}_p"] = row["p"]
        rows.append(wide)
        summaries.append(
            {
                "break_date": spec.break_date,
                "event": spec.label,
                "result": result,
                "param_df": param_df,
            }
        )

    results_df = pd.DataFrame(rows)
    csv_path = args.processed_dir / "table7_qmle_results.csv"
    results_df.to_csv(csv_path, index=False)
    print(f"\nwrote {csv_path}")

    # Render Table 7 markdown
    md_lines = []
    md_lines.append("# Table 7 (QMLE BEKK rebuild)\n")
    md_lines.append(
        "Real BEKK(1,1) QMLE re-estimated at three candidate break dates. "
        "Compare to Table 5 (paper's main BEKK result at break = 2023-10-23) and "
        "Table 7 (paper's footnoted *proxy* estimates).\n\n"
    )
    md_lines.append(
        "Headline parameters: `a12*`, `a21*` (short-run spillover shifts) and "
        "`g12*`, `g21*` (long-run spillover shifts). Significance: `*` p < 0.10, "
        "`**` p < 0.05, `***` p < 0.01.\n\n"
    )
    md_lines.append(
        "| Date | Event | a12\\* | a21\\* | g12\\* | g21\\* | log-lik | persistence (pre/post) |\n"
    )
    md_lines.append("|---|---|---|---|---|---|---|---|\n")
    for s in summaries:
        r = s["result"]
        df = s["param_df"]
        d = r.diagnostics
        idx_a12s = list(df["param"]).index("a12_star")
        idx_a21s = list(df["param"]).index("a21_star")
        idx_g12s = list(df["param"]).index("g12_star")
        idx_g21s = list(df["param"]).index("g21_star")
        md_lines.append(
            f"| {s['break_date']} | {s['event']} | "
            f"{_format_param(df.iloc[idx_a12s]['est'], df.iloc[idx_a12s]['p'])} | "
            f"{_format_param(df.iloc[idx_a21s]['est'], df.iloc[idx_a21s]['p'])} | "
            f"{_format_param(df.iloc[idx_g12s]['est'], df.iloc[idx_g12s]['p'])} | "
            f"{_format_param(df.iloc[idx_g21s]['est'], df.iloc[idx_g21s]['p'])} | "
            f"{-r.optim.nll:.2f} | "
            f"{d.persistence:.4f} / {d.persistence_post_break:.4f} |\n"
        )

    md_lines.append("\n## Full parameter table per break date\n")
    for s in summaries:
        md_lines.append(f"\n### {s['break_date']} — {s['event']}\n\n")
        md_lines.append("| Param | Est | SE | z | p | sig |\n")
        md_lines.append("|---|---|---|---|---|---|\n")
        for _, row in s["param_df"].iterrows():
            md_lines.append(
                f"| {row['param']} | {row['est']:+.4f} | {row['se']:.4f} | "
                f"{row['z']:+.2f} | {row['p']:.4f} | {row['sig']} |\n"
            )

    md_path = args.tables_dir / "table7_qmle.md"
    md_path.write_text("".join(md_lines))
    print(f"wrote {md_path}")

    # Narrative analysis
    paper_table5 = {
        "a12_star": -0.259,
        "a21_star": -0.196,
        "g12_star": +0.038,
        "g21_star": +0.054,
    }
    analysis_lines = []
    analysis_lines.append("# Table 7 (QMLE BEKK) — Analysis\n\n")
    analysis_lines.append(
        "The original Table 7 used a footnoted *proxy* estimator (OLS regressions on "
        "lagged residual products and dummy interactions). This version replaces the "
        "proxy with a real BEKK(1,1) QMLE re-estimated at each candidate break date.\n\n"
    )

    analysis_lines.append("## Comparison to paper Table 5 (break = 2023-10-23)\n\n")
    analysis_lines.append(
        "The paper's headline parameters (Table 5, break = 2023-10-23):\n"
    )
    for k, v in paper_table5.items():
        analysis_lines.append(f"- `{k}` = {v:+.3f}\\*\\*\\*\n")

    paper_row = next(s for s in summaries if str(s["break_date"]) == "2023-10-23")
    df = paper_row["param_df"]
    analysis_lines.append("\nPython port at the same break date:\n")
    for k in HEADLINE_PARAMS:
        idx = list(df["param"]).index(k)
        est = df.iloc[idx]["est"]
        sig = df.iloc[idx]["sig"]
        analysis_lines.append(f"- `{k}` = {est:+.4f}{sig}\n")
    analysis_lines.append(
        "\nIf the four headline signs match and magnitudes are within ~50% of the paper, "
        "the port is consistent with the paper's main result.\n"
    )

    analysis_lines.append("\n## Robustness across break dates\n\n")
    analysis_lines.append(
        "The point of Table 7 is to show whether the spillover shifts at "
        "2023-10-23 are unique or whether nearby ETF-related dates produce similar "
        "spillover patterns. Read the headline-parameter columns above:\n\n"
    )
    analysis_lines.append(
        "- All four `*` parameters with consistent sign across the three dates "
        "would indicate the result is robust.\n"
        "- Different signs or magnitudes flipping across dates would indicate "
        "the 2023-10-23 break is not uniquely special.\n\n"
    )

    analysis_path = args.tables_dir / "table7_qmle_analysis.md"
    analysis_path.write_text("".join(analysis_lines))
    print(f"wrote {analysis_path}")


if __name__ == "__main__":
    main()
