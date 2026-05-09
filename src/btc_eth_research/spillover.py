"""BEKK-style spillover shift estimators for Table 7.

This module estimates auditable BEKK-style proxies for the Table 7 robustness
exercise. It is not a full multivariate BEKK maximum-likelihood optimizer; the
outputs are named as short-run and long-run spillover shifts because they map to
the interpretation of the paper's a* and g* terms.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def _ols_shift(
    frame: pd.DataFrame,
    dependent: str,
    base_terms: list[str],
    shift_term: str,
) -> tuple[float, float]:
    columns = [dependent, *base_terms, shift_term]
    model_frame = frame[columns].replace([np.inf, -np.inf], np.nan).dropna()
    if len(model_frame) < 20:
        return float("nan"), float("nan")

    x = sm.add_constant(model_frame[[*base_terms, shift_term]], has_constant="add")
    model = sm.OLS(model_frame[dependent], x).fit(cov_type="HC3")
    return float(model.params[shift_term]), float(model.pvalues[shift_term])


def estimate_spillover_shifts(residuals: pd.DataFrame, break_date: pd.Timestamp) -> dict[str, float]:
    """Estimate short-run and long-run BTC/ETH spillover shifts."""

    required = {"btc_resid", "eth_resid"}
    missing = required - set(residuals.columns)
    if missing:
        raise ValueError(f"Missing residual columns: {sorted(missing)}")

    frame = residuals.copy()
    frame.index = pd.to_datetime(frame.index)
    frame["post_break"] = (frame.index >= break_date).astype(int)

    frame["btc_sq"] = frame["btc_resid"] ** 2
    frame["eth_sq"] = frame["eth_resid"] ** 2
    frame["btc_shock_lag1"] = frame["btc_sq"].shift(1)
    frame["eth_shock_lag1"] = frame["eth_sq"].shift(1)

    frame["btc_var_lag1"] = frame["btc_sq"].ewm(alpha=0.1, adjust=False).mean().shift(1)
    frame["eth_var_lag1"] = frame["eth_sq"].ewm(alpha=0.1, adjust=False).mean().shift(1)

    frame["eth_shock_post"] = frame["eth_shock_lag1"] * frame["post_break"]
    frame["btc_shock_post"] = frame["btc_shock_lag1"] * frame["post_break"]
    frame["eth_var_post"] = frame["eth_var_lag1"] * frame["post_break"]
    frame["btc_var_post"] = frame["btc_var_lag1"] * frame["post_break"]

    a12_star, a12_p = _ols_shift(
        frame,
        dependent="btc_sq",
        base_terms=["btc_shock_lag1", "eth_shock_lag1", "post_break"],
        shift_term="eth_shock_post",
    )
    a21_star, a21_p = _ols_shift(
        frame,
        dependent="eth_sq",
        base_terms=["eth_shock_lag1", "btc_shock_lag1", "post_break"],
        shift_term="btc_shock_post",
    )
    g12_star, g12_p = _ols_shift(
        frame,
        dependent="btc_sq",
        base_terms=["btc_var_lag1", "eth_var_lag1", "post_break"],
        shift_term="eth_var_post",
    )
    g21_star, g21_p = _ols_shift(
        frame,
        dependent="eth_sq",
        base_terms=["eth_var_lag1", "btc_var_lag1", "post_break"],
        shift_term="btc_var_post",
    )

    return {
        "a12_star": a12_star,
        "a12_p": a12_p,
        "a21_star": a21_star,
        "a21_p": a21_p,
        "g12_star": g12_star,
        "g12_p": g12_p,
        "g21_star": g21_star,
        "g21_p": g21_p,
    }


def directional_label(
    values: list[float],
    p_values: list[float],
    *,
    expected_sign: int,
    strong_alpha: float = 0.05,
    weak_alpha: float = 0.10,
    noun: str,
) -> str:
    """Convert signed estimates and p-values into a paper-readable label."""

    clean_values = [value for value in values if np.isfinite(value)]
    clean_p = [p for p in p_values if np.isfinite(p)]
    if not clean_values:
        return f"{noun}: insufficient data"

    signed = [expected_sign * value for value in clean_values]
    if all(value > 0 for value in signed) and clean_p and all(p <= strong_alpha for p in clean_p):
        return f"Strong {noun}"
    if all(value > 0 for value in signed) and clean_p and any(p <= weak_alpha for p in clean_p):
        return f"Moderate {noun}"
    if np.nanmean(signed) > 0:
        return f"Weak {noun}"
    return f"No robust {noun}"

