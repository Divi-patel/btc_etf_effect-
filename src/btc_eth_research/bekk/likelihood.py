"""BEKK(1,1) Ht recursion and Gaussian quasi-log-likelihood.

H_t = C C' + A_t' eps_{t-1} eps_{t-1}' A_t  +  G_t' H_{t-1} G_t
A_t = A + D_t A_star,   G_t = G + D_t G_star

ℓ(theta) = -1/2 * sum_t [ ln det(H_t) + eps_t' H_t^-1 eps_t ]   + const

Reference: varx_garch_bekk.R:226-354.
"""

from __future__ import annotations

import numpy as np

from .parameterization import BEKKParams, unpack_params


_PD_EIG_FLOOR = 1e-8  # eigenvalue clip for positive-definiteness enforcement
_LARGE_PENALTY = 1e10


def _ensure_pd(M: np.ndarray) -> np.ndarray:
    """Project M onto the cone of symmetric PD matrices via eigenvalue clip."""
    M_sym = 0.5 * (M + M.T)
    w, V = np.linalg.eigh(M_sym)
    if np.all(w > _PD_EIG_FLOOR):
        return M_sym
    w_clipped = np.maximum(w, _PD_EIG_FLOOR)
    return V @ np.diag(w_clipped) @ V.T


def ht_recursion(
    eps: np.ndarray,
    dummy: np.ndarray,
    params: BEKKParams,
    *,
    h0: np.ndarray | None = None,
) -> np.ndarray:
    """Compute H_t for t = 1, ..., T given residuals and break dummy.

    Args:
        eps    : (T, 2) array of VAR-X residuals
        dummy  : (T,) 0/1 array — 1 if t >= break_date
        params : BEKKParams instance
        h0     : optional 2x2 initial covariance; defaults to sample covariance

    Returns:
        H : (T, 2, 2) array of conditional covariance matrices
    """
    T = eps.shape[0]
    if eps.shape[1] != 2 or dummy.shape[0] != T:
        raise ValueError("eps must be (T,2) and dummy (T,)")

    if h0 is None:
        h0 = np.cov(eps.T)
    H = np.zeros((T, 2, 2))
    H_prev = _ensure_pd(h0)

    CC = params.C @ params.C.T  # constant-term contribution
    A = params.A
    G = params.G
    A_star = params.A_star
    G_star = params.G_star

    for t in range(T):
        d = dummy[t]
        A_t = A + d * A_star
        G_t = G + d * G_star

        if t == 0:
            outer = np.outer(eps[0], eps[0])  # use today's epsilon as warm-start proxy
        else:
            outer = np.outer(eps[t - 1], eps[t - 1])

        H_t = CC + A_t.T @ outer @ A_t + G_t.T @ H_prev @ G_t
        H_t = _ensure_pd(H_t)
        H[t] = H_t
        H_prev = H_t

    return H


def negative_log_likelihood(
    theta: np.ndarray,
    eps: np.ndarray,
    dummy: np.ndarray,
    *,
    h0: np.ndarray | None = None,
) -> float:
    """Quasi-Gaussian negative log-likelihood (drop the (T)*log(2π) constant).

    Returns +inf if any H_t is non-PD or determinant non-positive (penalty).
    """
    try:
        params = unpack_params(theta)
        H = ht_recursion(eps, dummy, params, h0=h0)
    except np.linalg.LinAlgError:
        return _LARGE_PENALTY
    except ValueError:
        return _LARGE_PENALTY

    T = eps.shape[0]
    nll = 0.0
    for t in range(T):
        H_t = H[t]
        det = np.linalg.det(H_t)
        if det <= 0 or not np.isfinite(det):
            return _LARGE_PENALTY
        try:
            inv = np.linalg.inv(H_t)
        except np.linalg.LinAlgError:
            return _LARGE_PENALTY
        quad = float(eps[t] @ inv @ eps[t])
        nll += 0.5 * (np.log(det) + quad)
    if not np.isfinite(nll):
        return _LARGE_PENALTY
    return nll


def per_observation_log_likelihood(
    theta: np.ndarray,
    eps: np.ndarray,
    dummy: np.ndarray,
    *,
    h0: np.ndarray | None = None,
) -> np.ndarray:
    """Return ℓ_t for each t — used for sandwich SEs (score outer-product)."""
    params = unpack_params(theta)
    H = ht_recursion(eps, dummy, params, h0=h0)
    T = eps.shape[0]
    ll = np.zeros(T)
    for t in range(T):
        H_t = H[t]
        det = np.linalg.det(H_t)
        inv = np.linalg.inv(H_t)
        quad = float(eps[t] @ inv @ eps[t])
        ll[t] = -0.5 * (np.log(det) + quad)
    return ll
