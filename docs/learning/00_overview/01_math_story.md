# The Math Story, End to End

The paper is a chain of mathematical objects. Each stage takes the output of the previous stage as input and produces something the next stage needs. The crypto context — Bitcoin, Ethereum, ETF approval — is the dataset and the motivation, but the spine is econometrics. If you can read this document and reproduce the chain on a piece of paper without consulting `main_paper.md`, you understand the paper.

This is a no-code doc. Every later folder will dive into one stage with derivations, alternatives, and pitfalls.

---

## 0. Notation we will reuse

| Symbol | Meaning | Dimension | First appears |
| --- | --- | --- | --- |
| `P_t` | Price at time `t` | scalar (per asset) | raw data |
| `r_t` | Log return on day `t` | scalar (per asset) | stage 1 |
| `Y_t` | Return vector `(BTC_t, ETH_t)'` | 2×1 | stage 5 |
| `r_{t,j}` | Log return for the `j`-th 5-minute bucket inside day `t` | scalar | stage 3 |
| `n` | Number of intraday buckets per day (288 for 24-hr crypto) | integer | stage 3 |
| `RV_t` | Realized variance on day `t` | scalar (per asset) | stage 3 |
| `CV_t` | Continuous variation on day `t` (estimated by TBPV) | scalar | stage 3 |
| `JV_t` | Jump variation on day `t` | scalar | stage 3 |
| `τ` | Structural break date | calendar date | stage 4 |
| `D_t` | Break dummy: 0 if `t ≤ τ`, 1 if `t > τ` | scalar | stage 4 |
| `X_t` | Exogenous regressor vector `(D_t, VIX_{t-1})'` | 2×1 | stage 5 |
| `ε_t` | Residual shock vector from VAR-X | 2×1 | stage 5 |
| `H_t` | Conditional covariance matrix of `ε_t` | 2×2, PSD | stage 6 |
| `ρ_t` | Conditional correlation between BTC and ETH | scalar in (-1, 1) | stage 7 |
| `θ` | Full parameter vector for BEKK | high-dim | stage 6 |

The reader should feel comfortable that every symbol on the right side of a `=` has been defined on the left side somewhere previously. That is the invariant we will maintain.

---

## 1. Prices to log returns

The data start as price series `P^{BTC}_t`, `P^{ETH}_t`. Prices are not stationary — they trend up and down — and most econometric machinery wants stationary inputs. The first move is to convert prices into returns.

The paper uses **log returns**:

```text
r_t = log(P_t) - log(P_{t-1}) = log(P_t / P_{t-1}).
```

Three reasons log returns dominate simple returns `(P_t − P_{t-1})/P_{t-1}` in time-series econometrics:

1. **Time-additivity.** A multi-period log return is the sum of single-period log returns. Simple returns compound multiplicatively, which is awkward in linear models.
2. **Symmetry.** A doubling and a halving give log returns of `+ln 2` and `−ln 2`. Simple returns give `+1.0` and `−0.5`, which are not symmetric.
3. **Approximate stationarity.** For most financial series, log returns are approximately covariance-stationary; price levels are not.

We end this stage with two daily series — `r^{BTC}_t` and `r^{ETH}_t` — and, for stage 3, two five-minute series sampled 288 times per day.

Reference: `01_statistics/02_*` (regression and residuals will use these), `02_time_series/01_*` (stationarity).

---

## 2. The conditional view: why one number per day is not enough

Up to here, a junior analyst would reach for the sample mean and sample standard deviation of `r_t`. That is what Table 1 in the paper does, split before and after the break.

But that view treats every day as exchangeable. It hides the central abstraction in time-series finance: at any time `t`, the return `r_t` has a distribution **conditional on the past**:

```text
μ_t  = E[r_t | F_{t-1}]              (conditional mean)
σ_t² = Var[r_t | F_{t-1}]            (conditional variance)
```

Here `F_{t-1}` is the information set available just before time `t` — past returns, past prices, anything observable. Both `μ_t` and `σ_t²` can move from day to day. Volatility clustering — the empirical fact that big moves cluster together — is exactly `σ_t²` being predictable from past `σ²` and past shocks. A constant-`σ²` model cannot reproduce that.

The whole rest of the paper is two large modeling exercises sitting on top of this idea:

- **VAR-X** models `μ_t` for the *vector* `(BTC, ETH)`.
- **BEKK-GARCH** models the *full conditional covariance matrix* `H_t` of the residuals from VAR-X.

When we say "the math is more important than the topic," this is what we mean. The paper's whole point is that **the conditional joint distribution of `(BTC, ETH)` returns changes after `τ`** — and doing that justice requires modeling both the conditional mean and the conditional covariance, and letting both depend on the break date.

Reference: `02_time_series/02_*` (conditional moments).

---

## 3. Going inside the day: realized volatility and jumps

Daily returns give a one-number-per-day summary of variation. Five-minute returns give 288 numbers per day, and they unlock estimators that converge to *theoretical* objects defined on the underlying continuous-time price process.

The paper assumes prices follow a **semimartingale** with a continuous diffusion part and an occasional jump part. Quadratic variation `[r]` of such a process splits into:

```text
[r]_t  = IV_t  +  JV_t
```

- `IV_t` (integrated variance) — area under the spot-volatility-squared path on day `t`.
- `JV_t` — sum of squared jump sizes on day `t`.

Two estimators are central:

**Realized variance** (Andersen–Bollerslev):

```text
RV_t = sum_{j=1..n} r_{t,j}²       →   [r]_t   as n → ∞.
```

This converges to total quadratic variation — it does *not* separate IV from JV.

**Threshold bipower variation** (Corsi–Pirino–Reno) for the continuous part:

```text
TBPV_t = μ_1^{-2} * sum_{j=2..n} |r_{t,j-1}| * |r_{t,j}|
                    * I{r_{t,j-1}² ≤ ν_{j-1}} * I{r_{t,j}² ≤ ν_j}
```

with `μ_1 = E|N(0,1)| = √(2/π) ≈ 0.7979`. Two pieces of intuition:

1. The product `|r_{j-1}| · |r_j|` of two adjacent returns dampens the influence of any single huge return — if one of the pair is a jump, the *other* almost certainly is not, so the product stays controlled.
2. The threshold indicators `I{r² ≤ ν}` further censor returns that look too large to be diffusive. `ν` is typically a multiple of a local volatility estimate.

The jump part is then recovered by subtraction:

```text
JV_t = max(RV_t − CV_t, 0),
```

where `CV_t = TBPV_t`. The `max(·, 0)` is the naive estimator: jump variation is non-negative by construction, but `RV_t − CV_t` can go slightly negative in finite samples. Better jump tests (BNS, Lee–Mykland) exist; the paper does not use them, and `04_critical_reading.md` flags this.

Output of this stage: per-asset, per-day series of `RV_t`, `CV_t`, `JV_t`. The paper uses these to fill Table 2 (means before vs. after `τ`, with t-tests on the difference).

Reference: `03_returns_and_volatility/01_*`, `03_returns_and_volatility/02_*`.

---

## 4. The structural break: a date `τ` where parameters change

The paper claims the joint dynamics of BTC and ETH changed in October 2023. Stated formally, there is a date `τ` such that the data-generating process on `[0, τ]` differs in some parameters from the data-generating process on `(τ, T]`.

If `τ` is **known** (say, a regulatory event), this is easy to test — fit the model on each subsample and run a Chow-style F-test on parameter equality.

If `τ` is **unknown**, we have to *find* it. The paper uses:

```text
c(y_{u:v}) = rank(y_{u:v}) − E[rank(y_{u:v})]
```

This is the rank-based cost function in `ruptures.Binseg`. Binary Segmentation greedily picks the date that minimizes the within-segment cost. With `n_bkps=1`, it returns a single break date — the paper's October 23, 2023.

`τ` then re-enters the rest of the pipeline as the break dummy:

```text
D_t = 0 for t ≤ τ,    D_t = 1 for t > τ.
```

`D_t` shows up in *both* the conditional mean equation (VAR-X) and the conditional covariance equation (BEKK), via different parameters. That dual role is why a single break date is doing a lot of work in this paper.

Reference: `04_structural_breaks/01_*`.

---

## 5. The conditional mean: VAR-X

Stack BTC and ETH returns into the vector `Y_t = (BTC_t, ETH_t)'`. The paper specifies a first-order Vector Autoregression with an Exogenous block:

```text
Y_t = C + A · Y_{t-1} + B · X_t + ε_t,        ε_t ~ (0, Σ_ε)
```

where `X_t = (D_t, VIX_{t-1})'`. Written out:

```text
BTC_t = c_BTC + α_11 BTC_{t-1} + α_12 ETH_{t-1} + β_11 D_t + β_12 VIX_{t-1} + ε_{1,t}
ETH_t = c_ETH + α_21 BTC_{t-1} + α_22 ETH_{t-1} + β_21 D_t + β_22 VIX_{t-1} + ε_{2,t}
```

The coefficients `α_ij` capture lagged cross-asset return predictability. `β_·1` measures the level shift induced by the break in mean returns; `β_·2` measures sensitivity to the lagged VIX. Estimation is equation-by-equation OLS with HC3 robust standard errors (so heteroskedasticity in `ε_t` does not invalidate inference about the *mean* parameters).

The deliverable from this stage is twofold:

- a table of `(C, A, B)` estimates with robust SEs (Table 3 in the paper),
- a residual series `ε_t = Y_t − Ŷ_t` for use in the volatility stage.

Two diagnostic outcomes from Table 4 are critical to the handoff:
- The Ljung–Box test on residuals does **not** reject — VAR-X removes most predictable mean dynamics. ✓
- The ARCH-LM test on residuals **strongly** rejects — there is volatility clustering left in `ε_t`. This is the signal that a GARCH-family model on the residuals is needed.

Reference: `06_var_and_varx/01_*`, `06_var_and_varx/02_*`.

---

## 6. The conditional covariance: BEKK-GARCH with structural breaks

Now we model the 2×2 conditional covariance matrix `H_t = Cov(ε_t | F_{t-1})`. The paper uses BEKK(1,1) with a break-period adjustment:

```text
H_t = C' C
    + A_t' · ε_{t-1} ε_{t-1}' · A_t        (ARCH / short-run shock effects)
    + G_t' · H_{t-1} · G_t                 (GARCH / long-run persistence)
```

where:

```text
A_t = A + D_t · A*,
G_t = G + D_t · G*,
A* has zeros on the diagonal,
G* has zeros on the diagonal.
```

Why this parameterization?

1. **Positive-definite by construction.** `C'C` is PSD, and the `M' X M` quadratic-form sandwich preserves PSD on the right-hand side. Without this trick you would have to enforce PSD as a constraint at every optimization step.
2. **Direct spillover interpretation.** The off-diagonal entries of `A` and `G` describe how a shock to one asset affects the *other asset's* conditional variance. That is what "spillover" means in this paper.
3. **Break enters multiplicatively, on the spillover terms only.** `A*` and `G*` are forced to zero on the diagonal. So the break is allowed to change cross-asset transmission, not own-asset persistence — a deliberate identification choice.

Estimation: **QMLE** under conditional normality.

```text
ℓ(θ) = − ½ · sum_{t} [ ln det(H_t(θ)) + ε_t' · H_t(θ)^{-1} · ε_t ]
```

The paper minimizes `−ℓ(θ)` with L-BFGS-B (bounded quasi-Newton) starting from a grid-search initialization. Standard errors come from the **sandwich** estimator:

```text
VCOV(θ̂) = H^{-1} · B · H^{-1}
```

where `H` is the Hessian of `ℓ` and `B = sum of outer products of scores`. This protects inference against the (almost certain) violation of the conditional normality assumption — see Table 4 where Jarque–Bera massively rejects for VAR-X residuals.

Output (Table 5):
- own-asset ARCH terms `a_11, a_22`,
- own-asset GARCH terms `g_11, g_22`,
- cross-asset ARCH `a_12, a_21` (mostly insignificant) and break shifts `a_12*, a_21*` (significantly negative),
- cross-asset GARCH `g_12, g_21` and break shifts `g_12*, g_21*` (significantly positive).

The paper reads this as: short-run cross-asset spillovers weakened after the break, while long-run persistence linkages strengthened.

Reference: `05_likelihood_and_qmle/01_*`, `05_likelihood_and_qmle/02_*`, `07_garch_to_bekk/01_*`, `07_garch_to_bekk/02_*`, `07_garch_to_bekk/03_*`.

---

## 7. From `H_t` back to a one-number-per-day story: conditional correlation

For interpretation and Figure 5, the paper extracts the conditional correlation:

```text
ρ_t = h_{12,t} / sqrt(h_{11,t} · h_{22,t})
```

Pre-break, `ρ_t` sits above 0.8. Post-break, `ρ_t` becomes more variable and occasionally drops below 0.5. This is the most visually striking finding.

`ρ_t` is a derived quantity, not an estimated parameter. Whatever you say about `ρ_t` is only as reliable as the BEKK estimate of `H_t` itself. That includes the model-misspecification caveats from `05_likelihood_and_qmle/02_*`.

Reference: `07_garch_to_bekk/02_*` (and the DCC contrast — DCC models `ρ_t` *directly*, BEKK derives it from `H_t`).

---

## 8. Robustness: re-run the chain at alternate break dates

The paper picks `τ = 2023-10-23`. Two natural alternatives:

- `2023-08-29` — Grayscale's appellate ruling.
- `2024-01-10` — the official SEC ETF approval.

A complete robustness exercise re-runs **the entire pipeline** at each date: re-estimate VAR-X with the new dummy, re-estimate full BEKK with the new break date, recompute spillover deltas. The paper's Table 7 tries to do this, but the fine print admits that the spillover values are **proxy estimates from VAR-X residual shocks and lagged volatility terms**, not full QMLE BEKK re-estimations. That is a real methodological hole and `03_critical_reading.md` is built around it.

Reference: `04_structural_breaks/01_*` (multiple-break detection), `03_critical_reading.md`.

---

## 9. The pipeline in one diagram

```text
                       prices P_t
                            │
                  log returns r_t  ────────── Table 1 (summary stats)
                            │
            ┌───────────────┴───────────────┐
            │                               │
       daily series                  5-min series r_{t,j}
            │                               │
            │                          RV_t, CV_t, JV_t
            │                               │
            │                       Table 2, Figure 4
            │                               │
            └───────── break τ via rank-Binseg on prices ─────────┐
                                            │                     │
                                          D_t                     │
                                            │                     │
                                  VAR-X(1) on (BTC, ETH) ─── Table 3, 4
                                            │
                                       residuals ε_t
                                            │
                              BEKK(1,1) with A*, G* on D_t
                              QMLE + sandwich SEs
                                            │
                                Table 5 (main results)
                                Table 6 (residual diagnostics)
                                            │
                              ρ_t = h_12/√(h_11·h_22)  ─── Figure 5
                                            │
                              re-run pipeline at alternate τ
                                            │
                                       Table 7 (robustness)
```

---

## 10. The math objects table (one page, reread before each section)

| Object | Defined at | Consumed at | Why it matters |
| --- | --- | --- | --- |
| `P_t` | Raw data | Stage 1 | Starting point. |
| `r_t` (daily) | Stage 1 | Stages 2, 5 | Stationary input for mean modeling. |
| `r_{t,j}` (5-min) | Stage 1 | Stage 3 | High-frequency input for variance estimators. |
| `RV_t` | Stage 3 | Stage 3 (decomposition), Table 2, Table 7 | Total intraday variation. |
| `CV_t` (= TBPV_t) | Stage 3 | Stage 3 (decomposition), Table 2 | Continuous (diffusive) variation. |
| `JV_t = max(RV_t − CV_t, 0)` | Stage 3 | Table 2, Table 7 | Jump (discontinuous) variation. |
| `τ` | Stage 4 | Stages 5, 6 | Date at which parameters change. |
| `D_t` | Stage 4 | Stages 5, 6 | Encodes `τ` for regression. |
| `X_t = (D_t, VIX_{t-1})'` | Stage 5 | Stage 5 | Exogenous block in VAR-X. |
| `Y_t = (BTC_t, ETH_t)'` | Stage 5 | Stage 5 | Endogenous block in VAR-X. |
| `(C, A, B)` | Stage 5 | Stage 5 | VAR-X parameter estimates. |
| `ε_t` | Stage 5 | Stage 6 | VAR-X residuals — input to BEKK. |
| `H_t` | Stage 6 | Stage 6, 7 | Conditional covariance matrix. |
| `(C, A, G, A*, G*)` | Stage 6 | Stage 6 | BEKK parameter estimates. |
| `θ` | Stage 6 | Stage 6 | Stacked parameter vector for QMLE. |
| `ℓ(θ)` | Stage 6 | Stage 6 | Quasi log-likelihood objective. |
| `VCOV(θ̂)` | Stage 6 | Stage 6 (inference) | Sandwich-robust covariance for θ̂. |
| `ρ_t` | Stage 7 | Figure 5 | Conditional correlation, derived from `H_t`. |

---

## What to read next

If this story made sense, you can already follow the table-by-table logic in `main_paper.md`. To actually re-derive the pipeline yourself, read the topical folders in this order:

1. `01_statistics/` — probability, regression, robust SEs.
2. `02_time_series/` — stationarity, conditional moments, ARMA.
3. `03_returns_and_volatility/` — RV, TBPV, jump decomposition.
4. `04_structural_breaks/` — break detection and encoding.
5. `05_likelihood_and_qmle/` — likelihood, MLE, QMLE, sandwich SEs.
6. `06_var_and_varx/` — AR → VAR → VAR-X with exogenous regressors.
7. `07_garch_to_bekk/` — ARCH → GARCH → BEKK with breaks.

Then revisit `00_overview/03_critical_reading.md` to see where the paper itself is fragile, and `00_overview/02_toolkit_and_choices.md` to see what alternative tools were available at each stage.
