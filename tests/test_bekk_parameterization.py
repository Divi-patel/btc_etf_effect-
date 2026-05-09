"""Tests for the 15-parameter BEKK packing/unpacking."""

from __future__ import annotations

import numpy as np
import pytest

from btc_eth_research.bekk.parameterization import (
    BEKKParams,
    NUM_PARAMS,
    PARAM_NAMES,
    build_bounds,
    initial_guess,
    pack_params,
    unpack_params,
)


def test_param_count_and_names():
    assert NUM_PARAMS == 15
    assert len(PARAM_NAMES) == 15


def test_pack_unpack_roundtrip():
    rng = np.random.default_rng(0)
    theta = rng.normal(size=NUM_PARAMS)
    p = unpack_params(theta)
    theta_back = pack_params(p)
    np.testing.assert_allclose(theta_back, theta)


def test_unpack_zeroes_diagonals_of_star_matrices():
    rng = np.random.default_rng(1)
    theta = rng.normal(size=NUM_PARAMS)
    p = unpack_params(theta)
    # A_star and G_star must have zero diagonal by construction
    assert p.A_star[0, 0] == 0.0
    assert p.A_star[1, 1] == 0.0
    assert p.G_star[0, 0] == 0.0
    assert p.G_star[1, 1] == 0.0


def test_C_is_lower_triangular():
    theta = np.zeros(NUM_PARAMS)
    theta[0] = 0.5  # c11
    theta[1] = 0.1  # c21
    theta[2] = 0.3  # c22
    p = unpack_params(theta)
    assert p.C[0, 1] == 0.0  # upper-right must be zero
    assert p.C[0, 0] == 0.5
    assert p.C[1, 0] == 0.1
    assert p.C[1, 1] == 0.3


def test_bounds_length_and_signs():
    bnds = build_bounds()
    assert len(bnds) == NUM_PARAMS
    for lo, hi in bnds:
        assert lo < hi


def test_initial_guess_uses_chol():
    rng = np.random.default_rng(2)
    eps = rng.normal(size=(200, 2)) * np.array([0.02, 0.03])
    theta0 = initial_guess(eps)
    assert theta0.shape == (NUM_PARAMS,)
    p = unpack_params(theta0)
    # C should be a real Cholesky factor of cov(eps)
    Sigma_hat = np.cov(eps.T)
    np.testing.assert_allclose(p.C @ p.C.T, Sigma_hat, atol=1e-10)
    # Diagonal A starts at 0.3, diagonal G at 0.85
    assert p.A[0, 0] == pytest.approx(0.3)
    assert p.A[1, 1] == pytest.approx(0.3)
    assert p.G[0, 0] == pytest.approx(0.85)
    assert p.G[1, 1] == pytest.approx(0.85)
