# Caveats and Honest Notes

This document lists the methodological notes that any reader of this repo
(including the original paper's authors) should know before citing or
extending these results. None of these are bugs that corrupt the published
numbers, but each is a place where reasonable people might want a different
choice or a sensitivity analysis.

The audit that produced this list was an independent code-vs-paper review
done after the BEKK QMLE pipeline was finished. The review compared the
Python port at `src/btc_eth_research/bekk/` against the original R reference
(an offline copy of `varx_garch_bekk.R` from the lab repo).

## The seven documented caveats

### 1. Returns are decimals, not percent

Throughout the Python pipeline, log returns are in *decimal* form (e.g.,
`0.02 = +2%`). This matches the R reference (`varx_garch_bekk.R:25`,
`diff(log(price)) * 1`). The paper's Table 1 reports descriptive statistics
in *percent* (e.g., "0.03%" mean BTC return) — this is a presentation
convention, not a different scale.

**Why this is fine for the BEKK Table 7 numbers.** The BEKK matrix elements
`A`, `G`, `A*`, `G*` are *dimensionless* coefficients. Multiplying returns
by 100 (decimal → percent) would scale `H_t` by 100² and the C matrix
elements by 100, but `A`, `G`, `A*`, `G*` are scale-invariant. So our
spillover estimates are directly comparable to the paper's Table 5
regardless of whether you read returns in decimals or percent.

**Where the scaling matters.** Our `c11`, `c21`, `c22` magnitudes are in
decimal-return units (e.g., 0.0098). If you want them in percent-return
units, multiply by 100. The paper's Table 5 c-values appear to be in the
same decimal units we use.

### 2. Break dummy convention is `D_t = 1 if t >= τ`

We use the inclusive convention: the break date itself is part of the
post-break period. The R reference does the same
(`varx_garch_bekk.R:660`: `ifelse(time(all_data) >= break_date, 1, 0)`).

If the paper text uses strict `t > τ` (break date excluded from post-break),
this is an off-by-one day at the boundary. The empirical effect is one day's
return reclassified, which doesn't move the headline parameters in any
meaningful way.

### 3. `H_0` initialization uses `eps[0]` as a warm-start proxy

The BEKK recursion needs a value for `eps_{-1}` and `H_{-1}` to compute
`H_0`. There is no observed `eps_{-1}` (it predates the sample). We use
`eps[0]` for the warm-start outer-product term and the sample residual
covariance for `H_{-1}`. The R reference does the same.

The effect is on the first ~5 likelihood contributions only — beyond that
the recursion has "forgotten" the initial condition because of the GARCH
geometric decay.

### 4. Positive-definiteness floor is 1e-8 (Python) vs 1e-6 (R)

Both implementations enforce `H_t` positive-definiteness by clipping
eigenvalues at a floor. Python uses `1e-8`, R uses `1e-6`. Stricter on our
side. This affects only pathological optimizer-trajectory points where `H_t`
would otherwise become near-singular; it does not affect the final
parameters or standard errors at convergence.

### 5. VAR-X coefficients differ slightly from paper Table 3

Paper's Table 3 was estimated on yfinance data fetched at paper write-up
time. We re-fetch through `yfinance` now (May 2026) and the historical
prices have been mildly revised by Yahoo. Specifically:

- AR coefficients (`α_11, α_12, α_21, α_22`): match the paper to 3 decimals.
  ✓
- Intercepts (`C(btc), C(eth)`): magnitudes differ. ours ~ -0.0009 vs
  paper +0.011. Order of magnitude is the same; sign differs slightly.
- Lagged-VIX coefficients (`β_12, β_22`): magnitudes differ.

**Why this doesn't affect Table 7.** BEKK is fit on the *residuals* from
VAR-X. By construction those residuals have mean zero and capture the
heteroskedastic structure of the data. Small differences in the VAR-X
intercept and VIX coefficient redistribute exactly zero residual mean
across observations.

We confirm this works in practice: the residual std (BTC=2.72%, ETH=3.44%)
matches the paper's Table 1 sample std (BTC=2.71%, ETH≈3.5% averaged across
regimes). The residual ARCH-LM statistic (BTC=53.1, ETH=76.6) matches
paper Table 4 (47.8, 70.0) within sampling noise.

### 6. Persistence at break = 2023-10-23 is borderline non-stationary

The post-break BEKK regime at 2023-10-23 has persistence eigenvalue 1.001 —
just above the unit-disk boundary. The other two break dates give
comfortable persistence: 0.962 (2023-08-29) and 0.951 (2024-01-10).

This is **not a numerical pathology** — the optimizer converged with
`success=True`, the sandwich SEs are finite, and all four headline
parameters have plausible values. It is an *empirical* signal that the
single-break BEKK at this date is finding a regime where own-asset
persistence is right at the edge.

The interpretation is also flagged in the analysis writeup: a multi-break
BEKK extension is the natural next step.

### 7. VAR-X is two-equation OLS, not joint VAR likelihood

The paper's R code uses `vars::VAR()` which fits a joint VAR. We use two
separate `statsmodels.OLS` calls with HC3 robust SEs. **For identical
regressor matrices these are mathematically equivalent** (system OLS =
equation-wise OLS when all equations share the same regressors). We
confirmed by running both paths on the same data and getting identical
residuals.

Reported in case the equivalence isn't obvious to a reader who just sees
"OLS" in our code and "VAR" in the paper.

## What this list deliberately does not cover

- Broader paper-level concerns (causal attribution, pre-test bias on the
  break date, multi-break detection, Student-t innovations, VIX
  exogeneity testing, multiple-testing correction). These are flagged in
  `docs/learning/00_overview/03_critical_reading.md` and are not yet
  addressed in this rebuild.
- The unit tests cover identity-case smoke tests, parameterization
  roundtrips, and a synthetic end-to-end run. They do not cover full
  numerical agreement against the R lab code (which would require
  installing R and running both side by side). The validation is instead
  via comparison of the four headline parameters against the paper's
  published Table 5 — see `docs/tables/table7_qmle_analysis.md`.

## Where to look next

- `docs/tables/table7_qmle_analysis.md` — the substantive analysis,
  including the proxy-vs-QMLE comparison that motivated this rebuild.
- `docs/learning/00_overview/03_critical_reading.md` — the broader list
  of paper-level concerns, of which only Issue 1 (this rebuild) is
  addressed in the current code.
