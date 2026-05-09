# Table 7 (QMLE BEKK) — Analysis

## What changed

The paper's original Table 7 reports "BEKK-style proxy estimates from VAR-X
residual shocks and lagged volatility terms" (its own footnote). That proxy is
implemented in `src/btc_eth_research/spillover.py::estimate_spillover_shifts` —
four OLS regressions of squared residuals on lagged shocks plus dummy
interactions, with **no likelihood, no Hessian, no sandwich estimator**. It is
not BEKK, just a regression that happens to use BEKK-like variable names.

This rebuild replaces that proxy with a **real BEKK(1,1) QMLE** with break-shift
matrices `A*`, `G*`, custom log-likelihood, L-BFGS-B optimization, and
Bollerslev-Wooldridge sandwich standard errors — re-estimated independently at
each of three candidate break dates. The pipeline lives in
`src/btc_eth_research/bekk/`.

## Side-by-side: proxy vs. real QMLE at break = 2023-10-23

| Param | Paper proxy (Table 7) | Paper QMLE (Table 5) | Python QMLE (this) |
|---|---|---|---|
| `a12*` | −0.103, p=0.24 (insig) | **−0.259***, p<0.001 | **−0.243**, p=0.047 |
| `a21*` | −0.340, p=0.30 (insig) | **−0.196***, p<0.001 | **−0.299***, p=0.006 |
| `g12*` | **−0.149**, p=0.35 (insig, **NEG sign**) | **+0.038***, p<0.001 | **+0.057***, p=0.083 |
| `g21*` | **−0.578**, p=0.29 (insig, **NEG sign**) | **+0.054***, p<0.001 | **+0.047***, p=0.055 |

The paper's proxy table had the **wrong sign** on both long-run spillover
shifts and was insignificant on all four parameters — directly contradicting
the paper's own Table 5 and abstract claim. The Python QMLE rebuild produces
estimates in the right direction and within the same magnitude as Table 5.
The paper's empirical claim is now defensibly supported by Table 7, which
previously it was not.

## The headline three-break comparison

| Date | Event | a12\* | a21\* | g12\* | g21\* | log-lik | post-break persistence |
|---|---|---|---|---|---|---|---|
| 2023-08-29 | Grayscale court ruling | −0.165* | −0.244** | +0.045* | +0.042 | 6350.98 | 0.962 |
| **2023-10-23** | **ETF enthusiasm / DTCC / Grayscale closure** | **−0.243*** | **−0.299*** | **+0.057*** | **+0.047*** | **6356.06** | 1.001 |
| 2024-01-10 | Official SEC approval | −0.067 | −0.213** | +0.028 | +0.037* | 6344.20 | 0.951 |

Three findings:

1. **All four `*` parameters keep their sign at every break date.**
   Short-run spillover shifts (`a*`) all negative; long-run shifts (`g*`) all
   positive. The paper's economic story — short-run spillovers weaken,
   long-run linkages strengthen — is **robust across all three dates**.

2. **2023-10-23 has the highest log-likelihood (6356.06) and the most
   uniformly significant parameters** (4 of 4 significant at ≥10%).
   2024-01-10 has the lowest log-likelihood and only 2 of 4 parameters
   significant — `a12*` collapses to −0.067 (p=0.41). This supports the
   paper's choice of the October enthusiasm date over the January approval
   date as the structurally important regime change. The market had already
   adjusted by SEC approval day.

3. **Post-break persistence at 2023-10-23 = 1.001 — borderline non-stationary.**
   The other two dates give comfortable persistence (0.95–0.96). This is a
   real concern: the post-break BEKK regime at 2023-10-23 sits at the edge of
   the covariance-stationary region, suggesting either (a) genuinely high
   post-break volatility persistence or (b) a remaining structural feature
   (e.g., another smaller break) that the single-break model is forcing the
   `g11`, `g22` diagonals to absorb.

## What this rebuild does *not* address

These are still open robustness concerns flagged in
`docs/learning/00_overview/03_critical_reading.md`:

- **Issue 2** — pre-test bias: the break date 2023-10-23 was selected
  endogenously from the same data, then re-tested on it. We did not re-run
  the rank-Binseg here.
- **Issue 3** — QMLE is asymptotically valid under non-Gaussian innovations,
  but our Jarque-Bera tests at 2023-10-23 reject hard (BTC p=0.000,
  ETH p=0.000). A Student-`t` BEKK fit would corroborate or undercut the
  Gaussian-QMLE inference.
- **Issue 4** — placebo break test on equities/gold not run.
- **Issue 5** — Granger test on VIX not run.
- **Issue 7** — single-break forced. Multi-break Bai-Perron not tried.

The `g11+g22` near-unity persistence at the 2023-10-23 fit is a hint that
Issue 7 may matter. A multi-break extension is the natural next step.

## How to reproduce

```bash
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python scripts/fetch_yfinance_daily.py
.venv/bin/python scripts/run_table7_qmle.py
```

Compute time on a 2024 MacBook: ~3-4 minutes per break date, ~12 minutes
total. Each fit reports VAR-X residual diagnostics, full BEKK parameter
table with sandwich SEs, and post-fit Ljung-Box / Jarque-Bera / persistence
diagnostics.
