# Critical Reading: Where the Paper Is Fragile

This is the doc you will reread before re-running anything in this project. The paper makes a coherent story — break detection, jump-volatility decline, BEKK spillovers, conditional correlation shift. But on close reading there are at least eight load-bearing places where the analysis is doing more work than it should, or making a claim that is not actually supported by what was estimated.

This is not a critique of the paper as a paper. It is a critique of the paper as a *recipe* for producing the same conclusions on different data. We need this doc because the goal is to relearn the fundamentals well enough that the next iteration is methodologically defensible.

Each section below has the same shape:

1. **Claim** — what the paper says.
2. **Why it matters** — what depends on the claim.
3. **What is fragile** — the specific gap.
4. **What would actually be needed** — concrete fix or check.
5. **Topic file to study** — where in the curriculum the relevant machinery lives.

The order is by severity, not by paper-section order.

---

## Issue 1 — Table 7 spillovers are *not* QMLE BEKK estimates

> **Claim.** Table 7 reports robustness across alternative break dates by re-estimating BEKK-style spillover parameters at each candidate τ.
>
> **Why it matters.** Table 7 is the paper's primary robustness check. If Table 7 contradicts Table 5, that is a five-alarm signal about the main result.
>
> **What is fragile.** The footnote on Table 7 in `main_paper.md` says explicitly:
>
> > "Spillover deltas are BEKK-style proxy estimates from VAR-X residual shocks and lagged volatility terms; regenerate this table if the full recovered R QMLE BEKK estimator is ported or run in an R environment."
>
> So the spillover values in Table 7 are *not* full QMLE BEKK re-estimations. They are some auxiliary regression on residual products and lagged volatilities. The *jump-volatility deltas* in Table 7 are real (those come from re-running the RV/CV/JV decomposition with new partition dates), but the spillover columns are a different statistical object than Table 5.

Concretely:

| Source | What was estimated |
|---|---|
| Table 5 | Full BEKK(1,1) QMLE with `A`, `G`, `A*`, `G*`, sandwich SEs. |
| Table 7 spillover columns | "BEKK-style proxy" from VAR-X residual shocks and lagged volatility terms. |

This is the single biggest hole in the paper. The reader is invited to compare Table 7 to Table 5 directly, but the two tables estimate different things.

Worse: Table 7's spillover *signs* contradict Table 5's. In Table 5, `g_{12}* = +0.038` and `g_{21}* = +0.054`, both significant at 1%. In Table 7, *every* `g*` value across all three candidate dates is **negative**, and *none* of them is significant. If you read Table 7 as the right answer, the long-run-spillover story collapses. If you read Table 5 as the right answer, Table 7 is non-informative on the spillover question.

**What would actually be needed.** Re-estimate the *full* QMLE BEKK at each of the three candidate dates and re-emit Table 7 with the same statistical object as Table 5. Until that exists, no claim of robustness on spillovers is defensible.

**Topic files:** `07_garch_to_bekk/03_*` (full BEKK estimation), `05_likelihood_and_qmle/02_*` (QMLE inference).

---

## Issue 2 — Pre-test bias in the structural break

> **Claim.** October 23, 2023 is a structural break.
>
> **Why it matters.** Every later table conditions on this date. If the date is wrong, the dummy is mis-aligned and `A*`, `G*` measurements are biased.
>
> **What is fragile.** The break date was *chosen using the same data* the rest of the paper analyzes. This is the classic pre-testing problem:
>
> 1. Run rank-Binseg on BTC daily prices with `n_bkps = 1`.
> 2. Get `τ̂ = 2023-10-23`.
> 3. Use `τ̂` as a regressor in VAR-X and BEKK.
> 4. Test whether the coefficient on the dummy is "significant."
>
> Step 4's null distribution is contaminated by step 1 — `τ̂` was *chosen to be where parameters look most different*. The reported p-values for `β_{·1}`, `a_{ij}*`, `g_{ij}*` are too small.

The honest fix is one of:

- Use a date selected by *external* information (e.g., Jan 10 SEC approval) and treat the break as known.
- Use a sup-Wald / Andrews test that explicitly accounts for the unknown break date.
- Use a holdout-data split: pick `τ̂` on one window, test on a different window.

The paper does none of these.

**What would actually be needed.** Re-run the analysis with `τ = 2024-01-10` (truly exogenous) and report whether the spillover shifts survive. If they do, the result is robust. If they don't, the Table 5 story is at least partly an artifact of pre-testing.

**Topic files:** `04_structural_breaks/01_*` (pre-test bias section), `01_statistics/02_*` (inference under model selection).

---

## Issue 3 — QMLE under non-Gaussian residuals

> **Claim.** QMLE with sandwich SEs makes BEKK estimation robust to non-normality.
>
> **Why it matters.** Crypto returns are clearly non-Gaussian (Table 4: Jarque–Bera rejects at p < 0.001 for both BTC and ETH residuals). If QMLE inference is unreliable, every BEKK p-value in Table 5 is up for grabs.
>
> **What is fragile.** QMLE consistency requires correct specification of the *first two conditional moments*. Sandwich SEs adjust the *variance* of the QMLE estimator, but they do not fix the estimator itself if the conditional mean or conditional covariance is misspecified. JB rejection is a non-normality signal, but it can also indicate:
>
> - missing higher-order terms in `H_t` (asymmetry / leverage effects),
> - omitted regimes,
> - heavy-tailed innovations whose variance is poorly identified by Gaussian quasi-likelihood.

A more honest treatment would re-estimate BEKK with Student-`t` innovations and compare:

```text
ε_t | F_{t-1}  ~  t_ν(0, H_t),    ν >> 4 ideally.
```

This gives back full likelihood-based inference (no sandwich needed), and the parameter `ν̂` itself reports the tail thickness the data prefer.

**What would actually be needed.** Either (a) fit BEKK-`t` and compare estimates and inference to Gaussian QMLE; or (b) bootstrap (block bootstrap, since residuals are time-series correlated) to get distribution-free SEs. The paper does neither.

**Topic files:** `05_likelihood_and_qmle/02_*` (when sandwich is enough), `07_garch_to_bekk/03_*` (BEKK with non-Gaussian innovations).

---

## Issue 4 — Causal attribution of October 23 to ETF approval

> **Claim.** The structural break on Oct 23, 2023 corresponds to "heightened market enthusiasm for ETF approval, the DTCC IBTC listing tweet, and the Grayscale court case closure."
>
> **Why it matters.** The paper's title and entire framing rest on the claim that *the ETF event* caused the regime change.
>
> **What is fragile.** Three different events are coincident on or near Oct 23:
>
> - DTCC IBTC listing tweet (technically dated August, re-amplified Oct 23).
> - Grayscale lawsuit closure (Oct 23).
> - Generic ETF anticipation (continuous through Q4 2023).
>
> The break detector finds *one* date. Attributing that date to *one* of the three events — or to ETF anticipation in general — is a narrative choice. The data do not isolate which.

Worse, there is at least one alternative explanation that the paper does not consider: **macro-driven crypto rally**. Treasury yields peaked around Oct 19, 2023 and reversed through Q4. A decline in real rates is a known driver of risk-asset rallies generally, not just crypto. If you regressed BTC returns on yield changes through this window, you might find a substantial portion of the post-Oct-23 dynamics is explained by macro, not regulatory news.

**What would actually be needed.**

- Run the same break detector on BTC excess returns (over a macro factor model) — does the Oct 23 break survive once macro is netted out?
- Run a placebo break detector on a non-ETF asset (S&P 500, gold) over the same window — does anything else show a break at Oct 23?
- Examine the rank-Binseg cost function around Oct 23 — is the minimum sharp, or is there a flat valley extending through Q4 2023?

**Topic files:** `04_structural_breaks/01_*` (placebo tests), `02_time_series/02_*` (macro factor decomposition).

---

## Issue 5 — VIX exogeneity is asserted, not tested

> **Claim.** VIX is exogenous in the VAR-X model.
>
> **Why it matters.** If VIX is endogenous, the lagged-VIX coefficients in Table 3 are not what the paper claims they are.
>
> **What is fragile.** The paper writes:
>
> > "Bitcoin returns significantly respond to the lagged VIX index (β_{12} = -0.001, p = 0.014)."
>
> This is fine *as a description of the OLS coefficient*. But to interpret it as "broader market volatility affects crypto returns," you need VIX to be at least weakly exogenous to the crypto innovations `ε_t`. Using *lagged* VIX (predetermined) helps. But there is no Granger causality test BTC → VIX or ETH → VIX. There is no test of weak exogeneity.

In the modern era, large crypto moves can in fact briefly move the broader risk environment — large BTC drawdowns have correlated with global risk-off episodes. We cannot rule out reverse feedback without testing.

**What would actually be needed.** Run pairwise Granger tests `BTC → VIX` and `ETH → VIX` over the sample. If we cannot reject, the lagged-VIX-as-exogenous treatment is fine. If we *can* reject, the right tool is a small VAR including VIX as endogenous.

**Topic files:** `06_var_and_varx/02_*` (Granger causality and weak exogeneity).

---

## Issue 6 — Economic significance of the jump-volatility decline

> **Claim.** Jump volatility declined significantly post-break: BTC ΔJV = −0.005 (p = 0.049), ETH ΔJV = −0.013 (p = 0.007). This indicates "increased market maturity, fewer extreme price shocks."
>
> **Why it matters.** This is one of the paper's three headline findings.
>
> **What is fragile.** The numbers are statistically significant at the 5% / 1% level but **economically tiny**. Translating to annualized volatility units:
>
> - BTC pre-break JV mean = 0.024 (variance, daily, in `r²` units).
> - BTC post-break JV mean = 0.019.
> - In daily volatility (`√JV`), that is `√0.024 ≈ 0.155` vs. `√0.019 ≈ 0.138`. So daily *jump-vol* dropped from ~15.5% to ~13.8%.
> - In annualized terms (× `√252`): from 246% to 219%.
>
> A 27-percentage-point drop in *annualized* jump-vol *does* sound economically meaningful. But the units are not what most readers would intuitively expect — those are *jump* contributions to daily variance, not total daily variance. A reader who walks away thinking "BTC volatility dropped 5% post-ETF" has the wrong picture.

The paper does not give the annualized translation, so the reader cannot easily judge the magnitude. This is more a presentation issue than a methodological one — but the *interpretation* in the abstract ("significant decline ... market maturity") leans on the reader doing this conversion in their head.

**What would actually be needed.** Append annualized vol columns to Table 2. Discuss the magnitude in terms readers can compare to (e.g., S&P 500 typical realized vol ≈ 15% annualized; BTC's 200%+ annualized jump-vol is still much higher even *post-break*).

**Topic files:** `03_returns_and_volatility/01_*` (vol annualization conventions).

---

## Issue 7 — Single break forced; multi-break alternative untested

> **Claim.** `n_bkps = 1`. There is one break, on October 23.
>
> **Why it matters.** If the data actually contain two breaks (Aug 29 ruling and Jan 10 approval), forcing one will produce a single artificial date that is not where any single regime actually changed. Every downstream coefficient is then attached to the wrong dummy.
>
> **What is fragile.** Binseg with `n_bkps = 1` is a *constraint*, not an inference. The procedure does not test whether one break is enough; it just gives you one. To know whether the data prefer one, two, or zero breaks, you need either:
>
> - Bai–Perron with information-criterion-based selection of the number of breaks,
> - Binseg/Dynp with `n_bkps` chosen by penalized likelihood (e.g., BIC penalty),
> - Visual inspection of the cost-function curve as `n_bkps` varies.

None of this is in the paper.

**What would actually be needed.** Re-run the break detector with `n_bkps ∈ {0, 1, 2, 3}`, plot the cost-vs-`n_bkps` elbow, and report which `n_bkps` an information criterion picks. If two breaks fit substantially better, the entire paper needs a two-break VAR-X / BEKK extension.

**Topic files:** `04_structural_breaks/01_*` (model selection over number of breaks).

---

## Issue 8 — The break dummy enters two equations, with constrained `A*`, `G*`

> **Claim.** The break enters via `D_t` in both VAR-X (`β_{11}`, `β_{21}`) and BEKK (`A*`, `G*` with zero diagonals).
>
> **Why it matters.** A break that affects "everything" in both mean and variance is doing a lot of explanatory work for one calendar date. Two related concerns:

> **What is fragile, part A — joint shift in mean *and* variance.** A single date is being asked to absorb a level shift in returns *and* a structural change in covariance. If only the covariance changed, but the dummy in the mean equation is forced in anyway, the VAR-X coefficient `β_{·1}` will pick up a small spurious mean shift. Conversely, if only the mean shifted, the BEKK `A*`, `G*` will pick up nothing or noise.

> **What is fragile, part B — zero diagonals on `A*` and `G*`.** Equation (9) of the paper writes `A*` and `G*` with zero on the diagonals — i.e., own-asset persistence is held constant across the break. This is an *a priori* assumption, not a result. There is no economic argument given for why ETF approval should change cross-asset transmission but not own-asset persistence. A more agnostic specification would estimate full `A*` and `G*` and let the data say which entries shifted.

**What would actually be needed.** Two falsifiability checks:

- Re-estimate VAR-X without `D_t` in the mean equation, then re-estimate BEKK with the dummy only in the variance equation. Does the conclusion survive?
- Re-estimate BEKK with full (non-zero-diagonal) `A*` and `G*`. Test which break-shift parameters are individually significant.

If both checks hold up, the paper's specification is fine. If they don't, the headline result needs to be qualified.

**Topic files:** `06_var_and_varx/02_*` (where the break enters VAR-X), `07_garch_to_bekk/03_*` (full vs. constrained break-shift BEKK).

---

## Other smaller issues worth flagging

These are not full issues on their own but should appear as footnotes in the topic files:

- **Joint coverage of significance levels.** Across Tables 3, 5, 6, 7, the paper reports many p-values; no multiple-testing adjustment is applied. With 10+ structural-break parameters and several diagnostic tests, a Bonferroni or Benjamini–Hochberg correction would tighten claims that are reported at the 5% or 10% level.
- **No out-of-sample test.** Every estimate is in-sample. A pseudo-out-of-sample exercise (estimate on `[2022-06, 2023-10]`, predict `[2023-10, 2024-06]`) would be far more compelling than Table 7. The paper does not do this.
- **No confidence band on `ρ_t`.** Figure 5 is a point-estimate path. Without a band, the visual claim "drops below 0.5" cannot be distinguished from estimator wobble.
- **Asset ordering matters in BEKK.** The off-diagonal entries `a_{12}` vs. `a_{21}` are *not* symmetric in BEKK; their interpretations depend on whether `Y_t = (BTC, ETH)'` or `(ETH, BTC)'`. The paper documents the ordering, but a reader who does not check carefully can flip the spillover direction in their head.
- **Threshold function ν in TBPV.** No sensitivity analysis to the choice of `ν`. Different conventions (constant multiple of local std, Andersen–Dobrev–Schaumburg adaptive) can move JV by tens of percent.
- **5-min sampling on a 24/7 market.** The 288-buckets-per-day choice is reasonable, but no sensitivity to coarser (15-min) or finer (1-min) sampling is reported. Microstructure noise is small at 5-min in liquid crypto, but this should be checked.

---

## What this critique implies for the *Execute → Feedback* phase

The plan's Feedback phase will produce a "what to actually re-run" doc. Based on the issues above, the priority list is:

1. **Re-run the full QMLE BEKK at all three candidate dates** to give Table 7 the same statistical object as Table 5 (Issue 1). This is the must-do fix.
2. **Run rank-Binseg with `n_bkps ∈ {0, 1, 2, 3}` and a BIC penalty**; report the chosen number (Issue 7).
3. **Run pairwise Granger tests `BTC ↔ VIX` and `ETH ↔ VIX`** to validate exogeneity (Issue 5).
4. **Refit BEKK with Student-`t` innovations** as a parallel to Gaussian QMLE (Issue 3).
5. **Refit BEKK with full `A*`, `G*`** (no zero-diagonal constraint) and report which entries shift (Issue 8).
6. **Add annualized-vol columns to Table 2** for economic interpretability (Issue 6).
7. **Run a placebo break detector on the S&P 500 and gold** over the same window to check for non-crypto-specific breaks at Oct 23 (Issue 4).
8. **Apply multi-test correction** to the BEKK p-values; report which entries survive (smaller issues list).

When you read this doc the next time, the goal is to argue the *severity* of each item (is it really blocking, or just a "nice to have"?) and to triage which fixes get done before any new claim is published.

---

## How this doc relates to the rest of the curriculum

Each issue points at a topic file. The point of `01_statistics/` through `07_garch_to_bekk/` is to give you the machinery to *evaluate* and *implement* these fixes. After you finish the curriculum, come back here and:

1. For each issue, decide if it's actually a problem now that you understand the math.
2. For each "what would actually be needed" suggestion, write the experiment plan.
3. Promote the survivors into a real `docs/learning/00_overview/04_next_steps.md` that drives the next iteration of the project.

This doc is intentionally written as a *reader's* critique, not a *defense* of the paper. The point is to be honest with yourself about what the original work proved and what it merely asserted.
