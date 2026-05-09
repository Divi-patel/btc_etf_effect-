"""Coarse grid search over diagonal A and G to seed L-BFGS-B.

Mirrors varx_garch_bekk.R:555-612. Off-diagonals are zeroed; A* and G* zeroed.
The C matrix is fixed to the Cholesky of the sample covariance of residuals.
"""

from __future__ import annotations

import numpy as np

from .likelihood import negative_log_likelihood
from .parameterization import BEKKParams, pack_params, NUM_PARAMS


def grid_search_initial(
    eps: np.ndarray,
    dummy: np.ndarray,
    *,
    grid_points: int = 5,
    a_range: tuple[float, float] = (0.05, 0.45),
    g_range: tuple[float, float] = (0.65, 0.95),
) -> tuple[np.ndarray, float]:
    """Search over diagonal A11, A22 in a_range and G11, G22 in g_range.

    Off-diagonals of A and G start at zero; A_star and G_star start at zero.
    C is fixed to chol(cov(eps)).

    Returns:
        best_theta : (15,) starting vector
        best_nll   : negative log-lik at best grid point
    """
    Sigma_hat = np.cov(eps.T)
    L = np.linalg.cholesky(Sigma_hat)

    a_grid = np.linspace(a_range[0], a_range[1], grid_points)
    g_grid = np.linspace(g_range[0], g_range[1], grid_points)

    best_nll = np.inf
    best_theta = None

    for a11 in a_grid:
        for a22 in a_grid:
            for g11 in g_grid:
                for g22 in g_grid:
                    p = BEKKParams()
                    p.C = L
                    p.A = np.diag([a11, a22])
                    p.G = np.diag([g11, g22])
                    p.A_star = np.zeros((2, 2))
                    p.G_star = np.zeros((2, 2))
                    theta = pack_params(p)
                    nll = negative_log_likelihood(theta, eps, dummy)
                    if nll < best_nll:
                        best_nll = nll
                        best_theta = theta

    if best_theta is None:
        raise RuntimeError("Grid search produced no finite likelihood — check residuals/data.")
    return best_theta, best_nll
