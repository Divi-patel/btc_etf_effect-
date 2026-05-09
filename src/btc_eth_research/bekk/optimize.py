"""L-BFGS-B wrapper for BEKK QMLE.

Mirrors varx_garch_bekk.R:356-368: bounded optimization with maxit=10000,
factr=1e8, pgtol=1e-6. SciPy's L-BFGS-B uses different option names:
    - factr   -> ftol (relative function-value tolerance, factr * eps_machine)
    - pgtol   -> gtol (projected-gradient tolerance)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from .likelihood import negative_log_likelihood
from .parameterization import build_bounds


@dataclass
class OptimResult:
    theta: np.ndarray           # final parameter vector
    nll: float                  # final negative log-lik
    success: bool               # convergence flag
    message: str                # optimizer message
    nit: int                    # iterations
    grad_norm: float            # final projected gradient norm (proxy for KKT)


def fit_qmle(
    theta_init: np.ndarray,
    eps: np.ndarray,
    dummy: np.ndarray,
    *,
    max_iter: int = 10000,
) -> OptimResult:
    """Run L-BFGS-B from a given starting point. Returns OptimResult."""
    bounds = build_bounds()

    def f(theta: np.ndarray) -> float:
        return negative_log_likelihood(theta, eps, dummy)

    result = minimize(
        f,
        theta_init,
        method="L-BFGS-B",
        bounds=bounds,
        options={
            "maxiter": max_iter,
            "ftol": 1e-8,
            "gtol": 1e-6,
        },
    )

    grad = result.jac if hasattr(result, "jac") and result.jac is not None else np.zeros_like(theta_init)
    grad_norm = float(np.linalg.norm(grad)) if grad is not None else float("nan")

    return OptimResult(
        theta=result.x,
        nll=float(result.fun),
        success=bool(result.success),
        message=str(result.message),
        nit=int(result.nit),
        grad_norm=grad_norm,
    )
