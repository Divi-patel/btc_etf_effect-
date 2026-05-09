# The Toolkit and the Choices We Made

`01_math_story.md` walked through what the paper does. This doc walks through **what could have been done at each stage, and why we picked what we picked**. It is a methods atlas, organized by pipeline stage. Each stage gets:

- the family of available tools,
- one-line descriptions of each tool,
- what the paper actually used and why,
- the cost we paid for that choice (no method is free).

If `01_math_story.md` is "what is the paper doing," this is "what was available on the shelf."

---

## Why this doc exists

When you write econometrics from scratch, you keep hitting decision points:

> "Daily or intraday? Log returns or simple? Single break or multiple? Chow or Bai–Perron? OLS or GLS? VAR or VECM? CCC, DCC, BEKK, GO-GARCH? MLE or QMLE? Gaussian or t-innovations? Bootstrap or sandwich?"

A reader of `main_paper.md` sees the answer ("we use this") but not the menu. That asymmetry is dangerous: it makes the choice look obvious when it was not. This doc puts the menu back on the table so that future-you can argue with past-you about whether the right thing was picked.

---

## Stage 1 — Returns

| Option | One-line description | Used? |
| --- | --- | --- |
| Simple returns `(P_t − P_{t-1}) / P_{t-1}` | Direct percentage change. Compounds multiplicatively across periods. | No |
| **Log returns `ln(P_t / P_{t-1})`** | Approximates simple returns for small moves; additive across time; symmetric in up/down moves. | **Yes** |
| De-meaned / standardized returns | Subtract sample mean (and optionally divide by sample std) before modeling. | Implicit at later stages |
| Excess returns over a risk-free rate | Common in equity finance; rarely used for crypto where `r_f` is poorly defined. | No |

**Why log returns:** time-additive, symmetric, approximately stationary. For a 5-minute series with 288 buckets per day, summing log returns gives the daily log return cleanly.

**The cost:** log returns are an *approximation* to simple returns. For a single 5-minute crypto bar that swings 30%, the approximation degrades. For a single daily 60% move (rare in BTC, possible in altcoins), `log(1.6) = 0.47` is genuinely different from `0.6`. We accept this because aggregation properties matter more than first-decimal accuracy.

---

## Stage 2 — Daily summary statistics

This is the descriptive layer that sits behind Table 1.

| Option | What it tells you | Used? |
| --- | --- | --- |
| **Mean, median, std dev** | Location and spread. | Yes |
| **Skewness, kurtosis** | Asymmetry and tail thickness. Crypto returns are notoriously fat-tailed. | Yes |
| Quantiles / IQR | Distribution-free spread; less sensitive to extremes than std dev. | Yes (Q1, Q3, IQR) |
| **Two-sample t-test** for equal means | Tests whether mean return is the same pre vs. post break. Assumes finite variance. | Yes |
| **Kolmogorov–Smirnov test** | Tests whether the *whole distribution* shifted. Distribution-free. | Yes (in lab folder 1) |
| Mann–Whitney / Wilcoxon | Rank-based location test. Robust to non-normality. | No |
| Anderson–Darling | More tail-sensitive than KS. | No |

**The cost of the t-test:** it tests means, not full distributional shifts. It will miss a regime change that leaves means alone but moves higher moments. The KS test in the lab folder partly fills that gap; Anderson–Darling would fill it better.

Reference: `01_statistics/02_*`.

---

## Stage 3 — High-frequency volatility

This is where the paper gets technical.

### 3a. Total intraday variation

| Option | One-line description | Used? |
| --- | --- | --- |
| **Realized variance `RV_t = Σ r_{t,j}²`** (Andersen–Bollerslev) | Converges to total quadratic variation as sampling gets fine. | **Yes** |
| Realized kernel (Barndorff-Nielsen–Hansen–Lunde–Shephard) | Robust to microstructure noise; appropriate when sampling at the tick. | No |
| Two-scale RV (Zhang–Mykland–Aït-Sahalia) | Same problem as realized kernel: noise-robust at very high frequencies. | No |

**Why plain RV:** at 5 minutes, microstructure noise in liquid crypto markets is small enough that plain RV is acceptable. At 1-second sampling we would have to switch to a noise-robust estimator. The 5-min choice is the standard "sweet spot" since Andersen–Bollerslev (1998).

### 3b. Splitting RV into continuous and jump

| Option | One-line description | Used? |
| --- | --- | --- |
| Bipower variation `BV` (Barndorff-Nielsen–Shephard 2004) | Uses products of *adjacent* absolute returns; one big jump in one position cancels out because the neighbor is almost certainly normal. | No |
| **Threshold bipower variation `TBPV`** (Corsi–Pirino–Reno 2010) | Adds an indicator that censors returns above a local volatility threshold `ν_j`. More robust than BV when jumps cluster. | **Yes** |
| MedRV (Andersen–Dobrev–Schaumburg) | Uses median rather than mean of consecutive squared returns. Robust to multiple jumps. | No |
| Realized semivariance | Splits RV by sign of return; useful for asymmetry studies. | No |

**Why TBPV:** the paper assumes crypto returns can have *clustered* jumps (a single news event triggers several large 5-min returns in a row). Plain BV's two-product trick fails when both factors are jumps. TBPV's threshold rule explicitly removes those.

**The cost:** TBPV depends on the threshold function `ν_j`. Different conventions (constant, local-vol-scaled, adaptive) give different jump estimates. The paper does not report sensitivity. `02_jumps_continuous_variation_tbpv.md` will cover the threshold-choice debate.

### 3c. Naming of the jump component

The paper sets `JV_t = max(RV_t − CV_t, 0)`. Alternatives:

| Option | One-line description | Used? |
| --- | --- | --- |
| **`JV = max(RV − CV, 0)`** (truncation) | Always non-negative. Biased upward in finite samples. | **Yes** |
| BNS jump test → keep `RV − CV` only on test-significant days | Statistical filtering. Identifies *which* days had jumps. | No |
| Lee–Mykland test | Spike-by-spike detection at the *intraday* level. | No |

**The cost of truncation:** you cannot tell jump activity from estimator noise; both raise `JV`. A test-based approach would tell you, "on day `t`, there is a 1% jump probability of zero," and treat the rest as zero by hypothesis. The paper trades that nuance for simplicity.

Reference: `03_returns_and_volatility/02_*`.

---

## Stage 4 — Structural break

| Option | One-line description | Used? |
| --- | --- | --- |
| **Chow test** (single known break) | F-test of equal coefficients on the two halves; needs `τ` known a priori. | No |
| **Bai–Perron** (multiple unknown breaks) | Simultaneously estimates the *number* and *locations* of breaks; relies on Gaussian-ish errors. | No |
| **CUSUM / CUSUM-Q** | Online detection of mean / variance shifts. | No |
| **Quandt likelihood ratio (QLR)** | Sup of Chow F-statistics over all candidate dates; does not require pre-specified `τ`. | No |
| **Binary segmentation (Binseg)** with Gaussian cost | Greedy split, fast, tractable; works on i.i.d. Gaussian assumption. | No |
| **Binary segmentation with rank cost** | Same algorithm, distribution-free cost; the choice for non-Gaussian data. | **Yes** |
| Dynamic programming (Dynp) | Exact minimum-cost partition under a chosen cost; slower than Binseg, more accurate when breaks are close together. | Used as cross-check in lab folder 2 |
| PELT (Killick–Fearnhead–Eckley) | Linear-time exact partition, more flexible cost function. | No |

**Why rank-Binseg:** non-Gaussian-robust (which crypto returns demand), fast (`O(n log n)` complexity), distribution-free in the cost function. Constraint: we have to *commit* to the number of breakpoints `n_bkps`. The paper sets `n_bkps = 1`, which forces a single break.

**The cost:** committing to a single break is a strong claim. If there are actually two breaks (e.g., an Aug 29 ruling and a separate Oct 23 enthusiasm event), forcing one will land somewhere in between or pick the larger one. Bai–Perron with information-criterion selection of the number of breaks would test that — the paper does not.

Reference: `04_structural_breaks/01_*`.

---

## Stage 5 — Conditional mean modeling

| Option | One-line description | Used? |
| --- | --- | --- |
| OLS per series | Treats each asset independently; ignores cross-asset effects. | No (too simple) |
| **VAR(p)** | Multivariate AR; lets BTC and ETH lags affect each other. | Sub-case |
| **VAR-X(p)** | VAR augmented with exogenous regressors (the X). | **Yes** |
| VARMA | VAR + MA terms; rarely outperforms VAR(p) in practice and is harder to estimate. | No |
| VECM | For *cointegrated* I(1) series; not appropriate for stationary returns. | No |
| ARDL / single-equation distributed lag | Cleaner identification but loses joint cross-asset structure. | No |

**Why VAR-X(1):** linear, tractable, easy to estimate equation-wise OLS. The lag length `p=1` is justified by Ljung–Box failing to reject autocorrelation in residuals (Table 4). The exogenous regressors `(D_t, VIX_{t-1})` let the break dummy and the broader macro volatility index enter without making them endogenous.

**The cost:** VAR-X assumes `X_t` is exogenous. The paper uses *lagged* VIX (predetermined), which helps, but no Granger / weak-exogeneity test is reported. If BTC actually moves the VIX (it does not, materially, but worth checking), the lagged-VIX coefficient is contaminated.

Reference: `06_var_and_varx/01_*`, `06_var_and_varx/02_*`.

---

## Stage 6 — Conditional covariance modeling

This is the densest decision tree in the paper.

### 6a. Univariate vs multivariate

| Option | What it gives you | Used? |
| --- | --- | --- |
| Two univariate GARCH(1,1) | Per-asset volatility paths; no covariance structure. | No |
| **Bivariate GARCH** | Volatility paths *plus* time-varying covariance. | **Yes** |

The paper's whole point is *cross*-asset spillover, which lives in the covariance, so univariate is not an option.

### 6b. Which multivariate GARCH

| Family | One-line description | Used? |
| --- | --- | --- |
| VECH / Diagonal VECH | Direct parameterization of `vech(H_t)`; positive-definiteness must be enforced. Many parameters. | No |
| **CCC** (Bollerslev) | Constant conditional correlation; fit univariate GARCHs and then a constant `R`. | No |
| **DCC** (Engle) | Dynamic conditional correlation; `H_t = D_t R_t D_t` with `D_t` from univariate GARCHs and `R_t` evolving. Two-stage estimation, scalable. | No |
| **BEKK** (Engle–Kroner) | `H_t = C'C + A' ε_{t-1} ε_{t-1}' A + G' H_{t-1} G`. PD by construction. Direct cross-asset parameters. | **Yes** |
| Diagonal BEKK | BEKK with diagonal `A`, `G`. Many fewer parameters. Loses cross-asset transmission interpretation. | No |
| Asymmetric BEKK / GARCH-in-mean / EGARCH cousins | Add leverage and mean-feedback. | No |
| GO-GARCH | Latent factor formulation. Cleaner for high `n`. | No |

**Why BEKK over DCC:** for a paper *about* spillovers, BEKK's off-diagonal `a_{12}, a_{21}, g_{12}, g_{21}` are first-class objects you can read directly. DCC tells you `ρ_t` evolves, but does not give you a coefficient that says "a shock to BTC raises ETH's volatility by *X*". The paper's headline claims (`a_{12}* = -0.259`, etc.) are BEKK numbers.

**The cost of BEKK:** parameter count. Even the bivariate full BEKK has 11 base parameters (3 in `C` lower triangle, 4 in `A`, 4 in `G`); the break extension adds 4 more (`a_{12}*, a_{21}*, g_{12}*, g_{21}*`). With ~625 daily observations, that is starting to push it. The likelihood surface can be flat in some directions, optimization is sensitive to starting values, and the variance of the estimates is large. In R, BEKK estimation routinely takes ~30 minutes per fit even for a bivariate model.

### 6c. The break-period extension

| Option | One-line description | Used? |
| --- | --- | --- |
| Estimate two BEKK models, one per regime | Cleanest interpretation; halves the data per fit. | No |
| **Single BEKK with `A_t = A + D_t · A*`, `G_t = G + D_t · G*`** | Pools data; adds 4 incremental parameters; tests `A* = G* = 0` directly. | **Yes** |
| Time-varying parameter BEKK (smoothly evolving) | Heaviest. Rarely worth it. | No |

The paper's choice trades full regime separation for statistical power — by pooling, every observation contributes to estimating `A` and `G`, while the post-break observations additionally identify `A*` and `G*`. That is the right tradeoff at this sample size.

### 6d. The `A*`, `G*` identification trick (zeros on the diagonal)

This is buried in equation (9) of the paper and matters more than it looks:

```text
A* has zero diagonal,    G* has zero diagonal.
```

Translation: only the *off-diagonal* (cross-asset spillover) terms are allowed to change at the break. Own-asset persistence (`a_{11}, a_{22}, g_{11}, g_{22}`) is held constant across regimes.

This is an **identifying assumption**, not a result. It is also a strong one — there is no a priori reason crypto's own-asset persistence should be constant across an institutional-adoption regime change. Relaxing this constraint (full `A*`, `G*`) would let the data speak; the paper does not check.

Reference: `07_garch_to_bekk/02_*`, `07_garch_to_bekk/03_*`.

---

## Stage 7 — Estimation and inference

### 7a. Mean-equation estimation

| Option | Used? |
| --- | --- |
| OLS with naive SEs | No |
| **OLS with HC0/HC1/HC2/HC3 robust SEs** (White; MacKinnon–White) | **Yes (HC3)** |
| GLS / WLS | No |
| GMM | No |

**Why HC3:** smaller-sample finite-sample correction over HC0/HC1/HC2. Standard choice in modern applied work.

### 7b. Variance-equation estimation

| Option | One-line description | Used? |
| --- | --- | --- |
| Full MLE assuming Gaussian innovations | Efficient if the distribution is correct. Wrong here. | No |
| **QMLE** (Bollerslev–Wooldridge) | Maximize Gaussian log-likelihood as an objective; rely on consistency of the conditional moments, not the distribution. | **Yes** |
| MLE with Student-`t` innovations | Closer to truth for fat tails; harder to optimize; gives back full likelihood-based inference. | No |
| Composite likelihood | Useful when full likelihood is intractable. Not needed here. | No |
| Bayesian (MCMC) | Posterior gives natural inference; computationally expensive. | No |

### 7c. Standard errors

| Option | Used? |
| --- | --- |
| MLE info-matrix SEs | No |
| **Sandwich (White, BHHH, Newey–West)** | **Yes (sandwich)** |
| Bootstrap | No |
| Block bootstrap (for time series) | No |

**Why sandwich:** consistent with the QMLE framing. If conditional mean and variance are correctly specified but the distribution is non-Gaussian, sandwich SEs remain valid; info-matrix SEs do not. Bootstrap would be more robust but adds heavy compute. `05_likelihood_and_qmle/02_*` discusses when sandwich is enough and when it is not.

---

## Stage 8 — Optimization

| Option | One-line description | Used? |
| --- | --- | --- |
| Grid search | Slow but globally informed; useful for *starting values*. | Yes (preliminary grid) |
| Newton-Raphson | Quadratic convergence near optimum; needs Hessian. | No |
| BFGS | Quasi-Newton with approximate Hessian; default in many libraries. | No |
| **L-BFGS-B** | Limited-memory BFGS with box constraints. | **Yes** |
| Nelder–Mead | Derivative-free; slow but robust. | Sometimes for sanity checks |
| Sequential quadratic programming (SQP) | Strong with constraints. | No |
| Differential evolution / global optimizers | Slow but global. | No |

**Why L-BFGS-B:** the BEKK parameter space is moderately large; BFGS-class methods scale well; box constraints help keep `(α + β) < 1` and similar stationarity conditions feasible. The "B" matters — without bounds, optimizers happily wander into PSD-violating regions.

**Cost:** local optimum risk. Mitigated by grid-search initialization, but not eliminated.

Reference: `05_likelihood_and_qmle/01_*`.

---

## Stage 9 — Software stack

The lab repo splits work across two languages:

| Component | Lab tool | Why |
| --- | --- | --- |
| Statistical summary, KS-test | Python (pandas, scipy) | Quick prototyping, plots in matplotlib. |
| Structural break | Python (`ruptures`) | Mature change-point library. |
| RV / TBPV / JV | Python (custom code) | Specialized formulas, easy to inspect. |
| **VAR-X + BEKK QMLE** | R (custom + `BEKK` ecosystem) | R has the most mature multivariate-GARCH stack; PD constraints, sandwich SEs, and L-BFGS optimization are well-trodden in R. |
| Tables and plots | Both | — |

**Why R for BEKK specifically:** the Python ecosystem (`arch`, `mgarch`) has good univariate GARCH but BEKK is sparse. Reimplementing PSD-constrained QMLE from scratch in Python is not impossible but is a real project. R's `BEKK`, `rmgarch`, and friends ship with the algebra and the optimizer hooks already correct.

The full justification lives in `docs/software_choices_r_vs_python.md` (moved out of the curriculum because it is a tooling decision, not learning material).

---

## Stage 10 — What the paper *did not* do (deliberate gaps)

These are not failures, but they are tools that were on the shelf and left there. Worth knowing they exist.

- **Realized covariance**: a multivariate analogue of RV from synchronized 5-min BTC and ETH returns. Would give a model-free conditional covariance to compare to BEKK's `H_t`.
- **Multivariate jump tests** (BNS-style joint tests): would tell you whether jumps are co-jumps or asset-specific.
- **DCC as a benchmark for ρ_t**: a quick DCC fit would either corroborate or undercut Figure 5's correlation pattern.
- **Forecasts and out-of-sample evaluation**: every parameter in the paper is estimated in-sample. A pseudo-out-of-sample exercise would provide a much stronger robustness story than Table 7.
- **Confidence bands on `ρ_t`**: Figure 5 is a point estimate path. Without a band you cannot say whether "0.5" is a real dip or estimator noise.
- **Multiple-testing correction**: across the BEKK estimation, several p-values < 0.001 are reported. With 10+ tested parameters and break extensions, a Bonferroni or FDR correction is appropriate.

---

## How to use this doc

When you write or revisit a topic file in `01–07/`, reread the relevant section here first. The mental sequence is:

1. *What is the menu?* (this doc)
2. *What was picked?* (this doc)
3. *Why?* (this doc, plus the topic file)
4. *What is the cost of that choice?* (this doc, then `00_overview/03_critical_reading.md`)
5. *How does it actually work?* (the topic file)

Choices that look obvious in retrospect were not obvious before. This doc is the antidote.
