"""BEKK(1,1) QMLE with structural-break shifts (A*, G*).

Pure-Python port of the lab R code at
`lab/Crypto-ETF-effect-and-Volatility-Modeling/4_VAR-X-GARCH-BEKK_for_btc_eth/varx_garch_bekk.R`.

Submodules:
- data           — yfinance daily panel loader
- parameterization — pack/unpack the 15-parameter vector
- likelihood     — Ht recursion + Gaussian quasi-log-likelihood
- grid_search    — coarse parameter grid for L-BFGS-B initialization
- optimize       — L-BFGS-B wrapper with bounds and convergence checks
- sandwich       — Hessian + score-outer-product → V = H^-1 B H^-1
- diagnostics    — Ljung-Box, JB, persistence eigvals
- fit            — high-level fit_bekk(returns, break_date)
"""
