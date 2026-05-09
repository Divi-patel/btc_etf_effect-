"""Bollerslev-Wooldridge sandwich standard errors for the BEKK QMLE.

Sandwich variance:
    V(theta_hat) = H^-1  B  H^-1
where:
    H = -E[ d2 log L / d theta d theta' ]    (negative Hessian of total log-lik)
    B = E[ score_t score_t' ]                (outer product of per-obs scores)

In finite samples we plug in:
    H_hat = - Hessian( log L )(theta_hat)            from numdifftools
    B_hat = sum_t score_t(theta_hat) score_t'(theta_hat)
where score_t = d log L_t / d theta is approximated by per-observation
numerical gradient.

Reference: varx_garch_bekk.R:383-406, 427-515.
"""

from __future__ import annotations

import numpy as np
import numdifftools as nd

from .likelihood import (
    negative_log_likelihood,
    per_observation_log_likelihood,
)


def _hessian_at(theta: np.ndarray, eps: np.ndarray, dummy: np.ndarray) -> np.ndarray:
    """Numerical Hessian of the *log-likelihood* (positive log-lik)."""
    def loglik(t: np.ndarray) -> float:
        return -negative_log_likelihood(t, eps, dummy)

    H_log = nd.Hessian(loglik, step=1e-4, method="central")(theta)
    return H_log


def _per_obs_scores(
    theta: np.ndarray,
    eps: np.ndarray,
    dummy: np.ndarray,
    *,
    h: float = 1e-5,
) -> np.ndarray:
    """Approximate score_t = d log L_t / d theta by central differences.

    Returns:
        S : (T, p) where p = len(theta).
    """
    p = len(theta)
    T = eps.shape[0]
    S = np.zeros((T, p))

    base = per_observation_log_likelihood(theta, eps, dummy)  # (T,)

    for k in range(p):
        theta_plus = theta.copy()
        theta_plus[k] += h
        theta_minus = theta.copy()
        theta_minus[k] -= h
        ll_plus = per_observation_log_likelihood(theta_plus, eps, dummy)
        ll_minus = per_observation_log_likelihood(theta_minus, eps, dummy)
        S[:, k] = (ll_plus - ll_minus) / (2 * h)

    # Sanity: column sums of S should be small at the (interior) optimum.
    return S


def sandwich_vcov(
    theta_hat: np.ndarray,
    eps: np.ndarray,
    dummy: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (V, H, B) — sandwich variance and its components.

    V = H^-1 · B · H^-1  where  H = -Hessian(log L)(theta_hat),
                              B = sum_t score_t · score_t'.
    """
    # H = -Hessian of log-lik (positive curvature at a max)
    H = -_hessian_at(theta_hat, eps, dummy)

    S = _per_obs_scores(theta_hat, eps, dummy)
    B = S.T @ S

    H_inv = np.linalg.pinv(H)  # pseudo-inverse for safety near bound
    V = H_inv @ B @ H_inv
    return V, H, B


def standard_errors(V: np.ndarray) -> np.ndarray:
    """Pull standard errors from a (positive-semi-)definite vcov matrix."""
    diag = np.diag(V)
    # In small samples the sandwich V can have tiny negative diagonals from
    # numerical noise; clip to small positive before sqrt.
    diag_clipped = np.clip(diag, 1e-20, None)
    return np.sqrt(diag_clipped)
