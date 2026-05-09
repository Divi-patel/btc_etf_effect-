"""Post-fit diagnostics for BEKK(1,1).

References (R lab code): varx_garch_bekk.R:741-1052.
- Standardized residuals z_t = H_t^{-1/2} eps_t
- Ljung-Box on z and z^2
- Jarque-Bera on z (per asset)
- Persistence: max eigenvalue of [kron(A, A) + kron(G, G)]; should be < 1
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox

from .likelihood import ht_recursion
from .parameterization import BEKKParams


@dataclass
class Diagnostics:
    standardized_residuals: np.ndarray   # (T, 2)
    ljung_box_z: dict                    # {asset: (stat, pvalue)}
    ljung_box_z2: dict                   # {asset: (stat, pvalue)}
    jarque_bera: dict                    # {asset: (stat, pvalue)}
    persistence: float                   # max eigenvalue of [kron(A,A)+kron(G,G)]
    persistence_post_break: float        # same with A_t, G_t at break
    nll: float
    aic: float
    bic: float


def standardized_residuals(eps: np.ndarray, H: np.ndarray) -> np.ndarray:
    """z_t = H_t^{-1/2} eps_t. Returns (T, 2)."""
    T = eps.shape[0]
    z = np.zeros_like(eps)
    for t in range(T):
        # Symmetric matrix square-root inverse via eigendecomposition
        H_sym = 0.5 * (H[t] + H[t].T)
        w, V = np.linalg.eigh(H_sym)
        w_clip = np.clip(w, 1e-12, None)
        H_inv_half = V @ np.diag(1.0 / np.sqrt(w_clip)) @ V.T
        z[t] = H_inv_half @ eps[t]
    return z


def persistence_eigenvalue(A: np.ndarray, G: np.ndarray) -> float:
    """max |eig(kron(A,A) + kron(G,G))|. Process is covariance stationary if < 1."""
    M = np.kron(A, A) + np.kron(G, G)
    return float(np.max(np.abs(np.linalg.eigvals(M))))


def compute_diagnostics(
    eps: np.ndarray,
    dummy: np.ndarray,
    params: BEKKParams,
    nll: float,
    n_params: int = 15,
    *,
    lb_lags: int = 10,
) -> Diagnostics:
    """Run all diagnostics. Returns a Diagnostics dataclass."""
    T = eps.shape[0]

    H = ht_recursion(eps, dummy, params)
    z = standardized_residuals(eps, H)

    # Ljung-Box on standardized residuals
    lb_z = {}
    lb_z2 = {}
    jb = {}
    for i, name in enumerate(("BTC", "ETH")):
        zi = z[:, i]
        lb1 = acorr_ljungbox(zi, lags=[lb_lags], return_df=True).iloc[0]
        lb_z[name] = (float(lb1["lb_stat"]), float(lb1["lb_pvalue"]))
        lb2 = acorr_ljungbox(zi ** 2, lags=[lb_lags], return_df=True).iloc[0]
        lb_z2[name] = (float(lb2["lb_stat"]), float(lb2["lb_pvalue"]))
        jb_stat, jb_p = stats.jarque_bera(zi)[:2]
        jb[name] = (float(jb_stat), float(jb_p))

    # Persistence at base (pre-break) and post-break
    pre = persistence_eigenvalue(params.A, params.G)
    post = persistence_eigenvalue(params.A + params.A_star, params.G + params.G_star)

    aic = 2 * n_params + 2 * nll
    bic = n_params * np.log(T) + 2 * nll

    return Diagnostics(
        standardized_residuals=z,
        ljung_box_z=lb_z,
        ljung_box_z2=lb_z2,
        jarque_bera=jb,
        persistence=pre,
        persistence_post_break=post,
        nll=nll,
        aic=aic,
        bic=bic,
    )
