"""Tests for the BEKK Ht recursion and quasi-log-likelihood."""

from __future__ import annotations

import numpy as np
import pytest

from btc_eth_research.bekk.likelihood import (
    ht_recursion,
    negative_log_likelihood,
    per_observation_log_likelihood,
)
from btc_eth_research.bekk.parameterization import BEKKParams, pack_params


def _gaussian_iid_nll(eps: np.ndarray, Sigma: np.ndarray) -> float:
    T = eps.shape[0]
    inv = np.linalg.inv(Sigma)
    det = np.linalg.det(Sigma)
    nll = 0.0
    for t in range(T):
        nll += 0.5 * (np.log(det) + eps[t] @ inv @ eps[t])
    return float(nll)


@pytest.fixture
def synthetic_eps():
    rng = np.random.default_rng(42)
    Sigma = np.array([[0.0007, 0.0008], [0.0008, 0.0012]])
    L = np.linalg.cholesky(Sigma)
    T = 500
    eps = (L @ rng.normal(size=(2, T))).T
    dummy = (np.arange(T) >= T // 2).astype(int)
    return eps, dummy, Sigma


def test_identity_case_Ht_equals_CCt(synthetic_eps):
    """If A = G = 0, then H_t = CC' for all t."""
    eps, dummy, Sigma = synthetic_eps
    L = np.linalg.cholesky(Sigma)
    p = BEKKParams()
    p.C = L
    p.A = np.zeros((2, 2))
    p.G = np.zeros((2, 2))
    H = ht_recursion(eps, dummy, p)
    expected = L @ L.T
    for t in range(eps.shape[0]):
        np.testing.assert_allclose(H[t], expected, atol=1e-10)


def test_identity_case_likelihood_matches_iid(synthetic_eps):
    """If A = G = 0, BEKK NLL should equal Gaussian-iid NLL."""
    eps, dummy, Sigma = synthetic_eps
    L = np.linalg.cholesky(Sigma)
    p = BEKKParams()
    p.C = L
    p.A = np.zeros((2, 2))
    p.G = np.zeros((2, 2))
    theta = pack_params(p)

    nll_bekk = negative_log_likelihood(theta, eps, dummy)
    nll_iid = _gaussian_iid_nll(eps, Sigma)
    assert abs(nll_bekk - nll_iid) < 1e-6


def test_per_obs_likelihood_sums_to_total(synthetic_eps):
    """sum of per-obs log-lik should equal -1 * negative_log_likelihood."""
    eps, dummy, _ = synthetic_eps
    rng = np.random.default_rng(1)
    p = BEKKParams()
    p.C = np.array([[0.02, 0.0], [0.01, 0.02]])
    p.A = np.diag([0.2, 0.2])
    p.G = np.diag([0.9, 0.9])
    theta = pack_params(p)

    nll = negative_log_likelihood(theta, eps, dummy)
    ll_per = per_observation_log_likelihood(theta, eps, dummy)
    assert abs(ll_per.sum() + nll) < 1e-6


def test_pd_enforcement_blocks_explosion():
    """An ill-conditioned start should not raise — likelihood returns finite or large penalty."""
    rng = np.random.default_rng(0)
    eps = rng.normal(size=(50, 2)) * 0.01
    dummy = np.zeros(50, dtype=int)
    p = BEKKParams()
    p.C = np.array([[1e-6, 0.0], [0.0, 1e-6]])
    p.A = np.array([[2.0, 0.0], [0.0, 2.0]])  # too large; H may blow up
    p.G = np.array([[0.99, 0.0], [0.0, 0.99]])
    theta = pack_params(p)

    nll = negative_log_likelihood(theta, eps, dummy)
    assert np.isfinite(nll)  # no NaN; either real value or large penalty
