"""15-parameter BEKK(1,1) with structural-break A*, G*.

Parameter layout (in fixed order):
    theta[0:3]   = (c11, c21, c22)                  lower-triangular C
    theta[3:7]   = (a11, a12, a21, a22)             full 2x2 ARCH matrix A
    theta[7:11]  = (g11, g12, g21, g22)             full 2x2 GARCH matrix G
    theta[11:13] = (a12_star, a21_star)             off-diagonal A* (post-break shift)
    theta[13:15] = (g12_star, g21_star)             off-diagonal G* (post-break shift)

H_t recursion (paper eq. 8 with regime-switching A_t, G_t):
    H_t = C C' + A_t' eps_{t-1} eps_{t-1}' A_t  +  G_t' H_{t-1} G_t
    A_t = A + D_t * A_star,    G_t = G + D_t * G_star
    A_star and G_star have zero diagonals (only off-diagonal shift).

Bounds match the R lab code (varx_garch_bekk.R:356-368).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


PARAM_NAMES: tuple[str, ...] = (
    "c11", "c21", "c22",
    "a11", "a12", "a21", "a22",
    "g11", "g12", "g21", "g22",
    "a12_star", "a21_star",
    "g12_star", "g21_star",
)
NUM_PARAMS = len(PARAM_NAMES)
assert NUM_PARAMS == 15


@dataclass
class BEKKParams:
    """Structured view of the 15-parameter BEKK(1,1) with break shifts."""

    C: np.ndarray = field(default_factory=lambda: np.zeros((2, 2)))
    A: np.ndarray = field(default_factory=lambda: np.zeros((2, 2)))
    G: np.ndarray = field(default_factory=lambda: np.zeros((2, 2)))
    A_star: np.ndarray = field(default_factory=lambda: np.zeros((2, 2)))
    G_star: np.ndarray = field(default_factory=lambda: np.zeros((2, 2)))

    def to_vector(self) -> np.ndarray:
        return pack_params(self)

    @classmethod
    def from_vector(cls, theta: np.ndarray) -> "BEKKParams":
        return unpack_params(theta)


def pack_params(p: BEKKParams) -> np.ndarray:
    """BEKKParams -> flat 15-vector in canonical order."""
    return np.array(
        [
            p.C[0, 0], p.C[1, 0], p.C[1, 1],
            p.A[0, 0], p.A[0, 1], p.A[1, 0], p.A[1, 1],
            p.G[0, 0], p.G[0, 1], p.G[1, 0], p.G[1, 1],
            p.A_star[0, 1], p.A_star[1, 0],
            p.G_star[0, 1], p.G_star[1, 0],
        ],
        dtype=float,
    )


def unpack_params(theta: np.ndarray) -> BEKKParams:
    """Flat 15-vector -> BEKKParams. Diagonals of A*, G* forced to zero."""
    if len(theta) != NUM_PARAMS:
        raise ValueError(f"Expected {NUM_PARAMS} parameters, got {len(theta)}")

    C = np.array([[theta[0], 0.0], [theta[1], theta[2]]])
    A = np.array([[theta[3], theta[4]], [theta[5], theta[6]]])
    G = np.array([[theta[7], theta[8]], [theta[9], theta[10]]])
    A_star = np.array([[0.0, theta[11]], [theta[12], 0.0]])
    G_star = np.array([[0.0, theta[13]], [theta[14], 0.0]])
    return BEKKParams(C=C, A=A, G=G, A_star=A_star, G_star=G_star)


def build_bounds() -> list[tuple[float, float]]:
    """L-BFGS-B bounds matching varx_garch_bekk.R:356-368."""
    bounds = [
        # C: lower-triangular Cholesky-like, allow negative covariance (c21)
        (-1.0, 1.0),  # c11
        (-1.0, 1.0),  # c21
        (-1.0, 1.0),  # c22
        # A diagonal in [0, 0.5], off-diagonal in [-0.15, 0.3]
        (0.0, 0.5),    # a11
        (-0.15, 0.3),  # a12
        (-0.15, 0.3),  # a21
        (0.0, 0.5),    # a22
        # G diagonal in [0.6, 0.98], off-diagonal in [-0.15, 0.3]
        (0.6, 0.98),   # g11
        (-0.15, 0.3),  # g12
        (-0.15, 0.3),  # g21
        (0.6, 0.98),   # g22
        # A_star, G_star off-diagonal in [-0.5, 0.5]
        (-0.5, 0.5),   # a12_star
        (-0.5, 0.5),   # a21_star
        (-0.5, 0.5),   # g12_star
        (-0.5, 0.5),   # g21_star
    ]
    assert len(bounds) == NUM_PARAMS
    return bounds


def initial_guess(eps: np.ndarray) -> np.ndarray:
    """Reasonable starting values: C from sample-cov Cholesky, A=G diagonal=0.3/0.85."""
    Sigma_hat = np.cov(eps.T)
    L = np.linalg.cholesky(Sigma_hat)  # lower triangular such that L L' = Sigma
    p = BEKKParams()
    p.C = L
    p.A = np.diag([0.3, 0.3])
    p.G = np.diag([0.85, 0.85])
    p.A_star = np.zeros((2, 2))
    p.G_star = np.zeros((2, 2))
    return pack_params(p)
