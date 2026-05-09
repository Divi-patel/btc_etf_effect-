"""End-to-end smoke test of the BEKK fit pipeline on a small synthetic series.

The full real-data fit at break = 2023-10-23 takes ~3-5 minutes. That is too
slow for the unit-test suite, so this test uses a 200-day synthetic process
and only checks that the pipeline runs and produces sensible outputs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from btc_eth_research.bekk.fit import fit_bekk
from btc_eth_research.bekk.parameterization import NUM_PARAMS


@pytest.fixture
def synthetic_panel():
    """Build a 200-day BTC/ETH-like panel with a regime change."""
    rng = np.random.default_rng(123)
    T = 200
    Sigma_pre = np.array([[0.0007, 0.0008], [0.0008, 0.0012]])
    Sigma_post = np.array([[0.0005, 0.0003], [0.0003, 0.0008]])

    halves = []
    L_pre = np.linalg.cholesky(Sigma_pre)
    L_post = np.linalg.cholesky(Sigma_post)
    for t in range(T):
        L = L_pre if t < T // 2 else L_post
        halves.append(L @ rng.normal(size=2))
    eps = np.array(halves)

    dates = pd.date_range("2023-01-01", periods=T, freq="D")
    panel = pd.DataFrame(
        {
            "btc_return": eps[:, 0],
            "eth_return": eps[:, 1],
            "vix_lag": rng.uniform(15, 25, size=T),
            "break_dummy": np.zeros(T, dtype=int),  # set inside fit_bekk
        },
        index=dates,
    )
    return panel


def test_fit_bekk_runs_end_to_end(synthetic_panel):
    """Full pipeline returns a valid result on synthetic data."""
    break_date = pd.Timestamp("2023-04-10")  # roughly mid-sample
    result = fit_bekk(
        break_date,
        panel=synthetic_panel,
        grid_points=3,  # smaller grid for speed
        max_iter=2000,
        verbose=False,
    )

    assert result.theta.shape == (NUM_PARAMS,)
    assert result.standard_errors.shape == (NUM_PARAMS,)
    assert result.p_values.shape == (NUM_PARAMS,)
    assert result.diagnostics.persistence < 1.5  # may be > 1 on tiny synthetic data
    assert np.all(np.isfinite(result.theta))
