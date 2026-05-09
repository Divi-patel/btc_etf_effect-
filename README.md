# BTC/ETH ETF Volatility-Spillover Research — Reproducible Rebuild

This repository rebuilds **Table 7** of the paper "Volatility Dynamics and
Spillovers in Cryptocurrency Markets: Evidence from the Bitcoin ETF
Approval" (Li, Patel, Koticha) using a real BEKK(1,1) QMLE estimator
re-estimated independently at three candidate break dates.

The published paper's Table 7 used a *proxy* estimator (acknowledged in its
own footnote) — OLS regressions of squared residuals on lagged shocks plus
dummy interactions, not a likelihood-based BEKK. This repo replaces that
proxy with a full QMLE BEKK port in pure Python, with Bollerslev–Wooldridge
sandwich standard errors and post-fit diagnostics.

## What's New: Real BEKK QMLE Table 7

Pipeline (all pure Python, no R dependency):

```
scripts/fetch_yfinance_daily.py      # daily BTC, ETH, VIX from yfinance
scripts/run_table7_qmle.py           # 3-break Table 7 generation
                                     #   (~12 min on a modern laptop)
```

Outputs:

```
data/processed/table7_qmle_results.csv     # wide table: params, SEs, p-values, diagnostics
docs/tables/table7_qmle.md                 # human-readable Table 7
docs/tables/table7_qmle_analysis.md        # narrative comparison vs the paper's Table 5
```

The core BEKK module lives at [`src/btc_eth_research/bekk/`](src/btc_eth_research/bekk/) — eight files
covering parameterization (15-parameter `C, A, G, A*, G*` layout), `H_t`
recursion, Gaussian quasi-log-likelihood, grid-search initialization,
L-BFGS-B optimization, sandwich SEs, diagnostics, and a high-level
`fit_bekk(break_date)` orchestrator.

For the seven documented methodological caveats, see [CAVEATS.md](CAVEATS.md).

## Quick Start

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
```

### Reproduce Table 7 (real QMLE)

```bash
.venv/bin/python scripts/fetch_yfinance_daily.py
.venv/bin/python scripts/run_table7_qmle.py
```

The first script writes `data/interim/yfinance_daily.parquet` (~30 KB,
945 rows of BTC/ETH/VIX daily closes from 2022-06-01 to 2024-12-31).

The second script fits BEKK QMLE three times — at break dates 2023-08-29,
2023-10-23, 2024-01-10 — and emits:

- `data/processed/table7_qmle_results.csv` — full parameter table.
- `docs/tables/table7_qmle.md` — markdown rendering with significance stars.
- `docs/tables/table7_qmle_analysis.md` — narrative comparing the three
  dates and contrasting with the paper's published numbers.

### Reproduce Table 2 (RV/CV/JV from 5-minute data)

```bash
.venv/bin/python scripts/fetch_binance_klines.py --start 2022-07 --end 2024-10 --symbols BTCUSDT ETHUSDT
.venv/bin/python scripts/run_table7.py
```

This is the *original* proxy-based Table 7 and the realized-volatility
panels (Table 2). The proxy script is kept in place for comparison; the
new QMLE pipeline above is independent of it.

## Repository Structure

```
src/btc_eth_research/
  bekk/                     ← NEW. Pure-Python BEKK QMLE pipeline.
    parameterization.py     ← 15-parameter C, A, G, A*, G* pack/unpack.
    likelihood.py           ← H_t recursion + Gaussian quasi-log-lik.
    grid_search.py          ← coarse 5^4 grid initialization.
    optimize.py             ← L-BFGS-B wrapper.
    sandwich.py             ← Bollerslev–Wooldridge sandwich SEs.
    diagnostics.py          ← Ljung-Box, Jarque-Bera, persistence eigvals.
    fit.py                  ← high-level fit_bekk(break_date) orchestrator.
    data.py                 ← yfinance daily panel loader.
  varx.py                   ← VAR-X mean equation (HC3 robust SEs).
  volatility.py             ← RV / CV (TBPV) / JV decomposition.
  spillover.py              ← The original OLS proxy (kept for comparison).
  table7.py                 ← Original Table 7 generator (proxy-based).
  binance.py, recovered.py, config.py

scripts/
  fetch_yfinance_daily.py   ← NEW. Daily BTC, ETH, VIX puller.
  run_table7_qmle.py        ← NEW. Real QMLE Table 7 driver.
  run_table7.py             ← Original (proxy-based) Table 7 driver.
  fetch_binance_klines.py   ← 5-min Binance klines (for Table 2).
  build_daily_panel.py
  import_recovered_artifacts.py
  run_table7_recovered.py
  smoke_test_sample.py

tests/
  test_bekk_likelihood.py        ← Identity-case smoke tests.
  test_bekk_parameterization.py  ← Pack/unpack roundtrip.
  test_bekk_endtoend.py          ← Full pipeline on synthetic data.
  test_volatility.py, test_table7.py, test_binance_parser.py

docs/
  main_paper.md             ← Paper text (markdown export).
  main_paper_media/         ← Paper figures.
  tables/
    table7_qmle.md          ← Real QMLE Table 7 (the deliverable).
    table7_qmle_analysis.md ← Narrative analysis with proxy-vs-QMLE comparison.
  learning/00_overview/
    01_math_story.md        ← The paper's math, end-to-end.
    02_toolkit_and_choices.md  ← Methods used and what alternatives existed.
    03_critical_reading.md  ← Eight known limitations / future-work items.
```

## Notes

- Raw and interim data are gitignored — the scripts above regenerate
  everything from scratch.
- The original lab repository (R/Python notebooks for the legacy
  pipeline) is referenced for context but **not** included in this
  repository. It lives at the original GitHub URL and was used here only
  to extract the BEKK formulation and parameter conventions.
- All tests pass: `.venv/bin/python -m pytest tests/` reports 19 of 19
  passing.
- The `docs/learning/` curriculum (math story, toolkit and choices,
  critical reading) is the first-principles study path that motivated
  this rebuild and lists the broader robustness checks (multi-break
  detection, Student-t innovations, VIX Granger test, etc.) that this
  rebuild deliberately leaves for future work.

## License

MIT — see [LICENSE](LICENSE).

## Citation

If you use this code in academic work, please cite the underlying paper:

> Li, J., Patel, D., and Koticha, A. (2026). Volatility Dynamics and
> Spillovers in Cryptocurrency Markets: Evidence from the Bitcoin ETF
> Approval.

Contact: Divykumar Patel (dpatel103@stevens.edu).
