"""High-level orchestrator: load panel -> VAR-X residuals -> BEKK -> SEs -> diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .data import load_aligned_panel
from .diagnostics import Diagnostics, compute_diagnostics
from .grid_search import grid_search_initial
from .likelihood import negative_log_likelihood
from .optimize import OptimResult, fit_qmle
from .parameterization import BEKKParams, PARAM_NAMES, NUM_PARAMS, unpack_params
from .sandwich import sandwich_vcov, standard_errors


@dataclass
class BEKKResult:
    break_date: pd.Timestamp
    theta: np.ndarray                  # (15,) parameter estimates
    standard_errors: np.ndarray        # (15,) sandwich SEs
    z_stats: np.ndarray                # theta / SE
    p_values: np.ndarray               # two-sided p-values
    params: BEKKParams                 # structured form
    optim: OptimResult
    diagnostics: Diagnostics
    n_obs: int
    var_summary: dict = field(default_factory=dict)  # VAR-X coefficient table
    residuals: pd.DataFrame | None = None


def _fit_varx(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Estimate VAR-X(1) on the panel and return (residuals_df, summary_dict).

    Mean equation:
        BTC_t = c + a11 BTC_{t-1} + a12 ETH_{t-1} + b11 D_t + b12 VIX_{t-1} + e1
        ETH_t = c + a21 BTC_{t-1} + a22 ETH_{t-1} + b21 D_t + b22 VIX_{t-1} + e2
    Estimated by OLS with HC3 robust SEs.
    """
    df = panel.copy()
    df["btc_lag1"] = df["btc_return"].shift(1)
    df["eth_lag1"] = df["eth_return"].shift(1)
    df = df.dropna()

    X = sm.add_constant(df[["btc_lag1", "eth_lag1", "break_dummy", "vix_lag"]])
    btc_model = sm.OLS(df["btc_return"], X).fit(cov_type="HC3")
    eth_model = sm.OLS(df["eth_return"], X).fit(cov_type="HC3")

    resid = pd.DataFrame(
        {
            "btc_resid": btc_model.resid,
            "eth_resid": eth_model.resid,
        },
        index=df.index,
    )
    summary = {
        "btc_params": dict(btc_model.params),
        "btc_pvalues": dict(btc_model.pvalues),
        "eth_params": dict(eth_model.params),
        "eth_pvalues": dict(eth_model.pvalues),
        "n_obs": len(df),
    }
    return resid, summary


def fit_bekk(
    break_date: date | pd.Timestamp,
    *,
    panel: Optional[pd.DataFrame] = None,
    grid_points: int = 5,
    max_iter: int = 10000,
    verbose: bool = True,
) -> BEKKResult:
    """End-to-end fit of the structural-break BEKK(1,1) at a candidate break date."""
    break_ts = pd.Timestamp(break_date)
    if panel is None:
        panel = load_aligned_panel(break_ts)
    else:
        panel = panel.copy()
        panel["break_dummy"] = (panel.index >= break_ts).astype(int)

    if verbose:
        print(f"[fit_bekk] break_date = {break_ts.date()}")
        print(f"[fit_bekk] panel rows = {len(panel)}")

    # 1. VAR-X residuals
    resid_df, var_summary = _fit_varx(panel)
    aligned = panel.loc[resid_df.index]
    eps = resid_df[["btc_resid", "eth_resid"]].values
    dummy = aligned["break_dummy"].values
    if verbose:
        print(f"[fit_bekk] VAR-X residuals: shape={eps.shape}, "
              f"BTC std={eps[:, 0].std():.6f}, ETH std={eps[:, 1].std():.6f}")

    # 2. Grid search for starting values
    if verbose:
        print(f"[fit_bekk] grid search ({grid_points}^4 = {grid_points**4} points)...")
    theta_init, nll_init = grid_search_initial(eps, dummy, grid_points=grid_points)
    if verbose:
        print(f"[fit_bekk] grid done. best initial NLL = {nll_init:.4f}")

    # 3. L-BFGS-B optimization
    if verbose:
        print(f"[fit_bekk] L-BFGS-B (max_iter={max_iter})...")
    optim = fit_qmle(theta_init, eps, dummy, max_iter=max_iter)
    if verbose:
        print(f"[fit_bekk] done. NLL = {optim.nll:.4f}, "
              f"iter={optim.nit}, success={optim.success}")

    # 4. Sandwich SEs
    if verbose:
        print(f"[fit_bekk] computing sandwich SEs...")
    V, _, _ = sandwich_vcov(optim.theta, eps, dummy)
    se = standard_errors(V)
    z_stats = optim.theta / np.where(se > 0, se, np.nan)
    from scipy.stats import norm as _norm
    p_values = 2 * (1 - _norm.cdf(np.abs(z_stats)))

    # 5. Diagnostics
    if verbose:
        print(f"[fit_bekk] computing diagnostics...")
    params = unpack_params(optim.theta)
    diag = compute_diagnostics(eps, dummy, params, optim.nll, n_params=NUM_PARAMS)

    return BEKKResult(
        break_date=break_ts,
        theta=optim.theta,
        standard_errors=se,
        z_stats=z_stats,
        p_values=p_values,
        params=params,
        optim=optim,
        diagnostics=diag,
        n_obs=eps.shape[0],
        var_summary=var_summary,
        residuals=resid_df,
    )


def render_param_table(result: BEKKResult) -> pd.DataFrame:
    """Tidy parameter table for printing or CSV export."""
    rows = []
    for name, est, se, z, p in zip(
        PARAM_NAMES,
        result.theta,
        result.standard_errors,
        result.z_stats,
        result.p_values,
    ):
        stars = "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.10 else ""))
        rows.append(
            {"param": name, "est": est, "se": se, "z": z, "p": p, "sig": stars}
        )
    return pd.DataFrame(rows)
