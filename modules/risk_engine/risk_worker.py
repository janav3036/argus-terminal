from dataclasses import dataclass

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
from PySide6.QtCore import QThread, Signal

LOOKBACK_PERIOD = "3y"
CONFIDENCE_LEVELS = [0.95, 0.99]
HORIZONS_DAYS = [1, 5]
MC_PATHS = 10_000
ROLLING_WINDOW = 252

@dataclass
class RiskResult:
    tickers: list[str]
    weights: np.ndarray
    dates: np.ndarray
    portfolio_returns: np.ndarray
    corr_matrix: np.ndarray
    var_table: dict
    cvar_table: dict
    rolling_var_dates: np.ndarray
    rolling_var_95: np.ndarray
    rolling_var_99: np.ndarray

def _fetch_portfolio_returns(tickers: list[str], weights: np.ndarray) -> tuple[np.ndarray, pd.DataFrame, np.ndarray]:
    prices = {}
    for ticker in tickers:
        bars = yf.Ticker(ticker).history(period=LOOKBACK_PERIOD, interval="1d")
        if bars.empty:
            raise ValueError(f"No price data found for '{ticker}' - check the ticker symbol")
        prices[ticker] = bars["Close"]

    price_df = pd.DataFrame(prices).dropna()
    returns_df = price_df.pct_change().dropna()

    dates = returns_df.index.to_numpy()
    portfolio_returns = returns_df.to_numpy() @ weights

    return dates, returns_df, portfolio_returns

def _historical_var_cvar(portfolio_returns: np.ndarray, horizon_days: int, confidence: float) -> tuple[float, float]:
    if horizon_days==1:
        horizon_returns = portfolio_returns
    else:
        horizon_returns = pd.Series(portfolio_returns).rolling(horizon_days).apply(
            lambda window: np.prod(1+window) - 1
        ).dropna().to_numpy()

    var = np.percentile(horizon_returns,(1-confidence)*100)
    cvar = horizon_returns[horizon_returns <= var].mean()
    return var, cvar

def _parametric_var_cvar(portfolio_returns: np.ndarray, horizon_days: int, confidence: float) -> tuple[float, float]:
    mu = portfolio_returns.mean() * horizon_days
    sigma = portfolio_returns.std() * np.sqrt(horizon_days)

    z = norm.ppf(1 - confidence)
    var = mu + z * sigma

    alpha = 1 - confidence
    cvar = mu - sigma * norm.pdf(z) / alpha

    return var, cvar

def _monte_carlo_var_cvar(returns_df: pd.DataFrame, weights: np.ndarray, confidence: float) -> tuple[float, float]:
    mu_vec = returns_df.mean().to_numpy()
    cov = returns_df.cov().to_numpy()

    L = np.linalg.cholesky(cov)
    z = np.random.standard_normal((MC_PATHS, len(weights)))
    simulated_returns = mu_vec + z @ L.T

    portfolio_sim = simulated_returns @ weights

    var = np.percentile(portfolio_sim, (1 - confidence) * 100)
    cvar = portfolio_sim[portfolio_sim <= var].mean()
    return var, cvar

def _rolling_var(portfolio_returns: np.ndarray, window: int, confidence: float) -> np.ndarray:
    return pd.Series(portfolio_returns).rolling(window).apply(
        lambda w: np.percentile(w, (1 - confidence) * 100)
    ).dropna().to_numpy()

class RiskWorker(QThread):
    finished_risk = Signal(object)
    failed = Signal(str)

    def __init__(self, tickers: list[str], weights: np.ndarray, parent=None):
        super().__init__(parent)
        self.tickers = tickers
        self.weights = weights

    def run(self):
        try:
            dates, returns_df, portfolio_returns = _fetch_portfolio_returns(self.tickers, self.weights)
            corr_matrix = returns_df.corr().to_numpy()

            var_table = {"historical": {}, "parametric": {}, "monte_carlo": {}}
            cvar_table = {"historical": {}, "parametric": {}, "monte_carlo": {}}

            for horizon in HORIZONS_DAYS:
                var_table["historical"][horizon] = {}
                cvar_table["historical"][horizon] = {}
                var_table["parametric"][horizon] = {}
                cvar_table["parametric"][horizon] = {}
                for confidence in CONFIDENCE_LEVELS:
                    var, cvar = _historical_var_cvar(portfolio_returns, horizon, confidence)
                    var_table["historical"][horizon][confidence] = var
                    cvar_table["historical"][horizon][confidence] = cvar

                    var, cvar = _parametric_var_cvar(portfolio_returns, horizon, confidence)
                    var_table["parametric"][horizon][confidence] = var
                    cvar_table["parametric"][horizon][confidence] = cvar

            var_table["monte_carlo"][1] = {}
            cvar_table["monte_carlo"][1] = {}
            for confidence in CONFIDENCE_LEVELS:
                var, cvar = _monte_carlo_var_cvar(returns_df, self.weights, confidence)
                var_table["monte_carlo"][1][confidence] = var
                cvar_table["monte_carlo"][1][confidence] = cvar

            rolling_var_dates = dates[ROLLING_WINDOW - 1:]
            rolling_var_95 = _rolling_var(portfolio_returns, ROLLING_WINDOW, 0.95)
            rolling_var_99 = _rolling_var(portfolio_returns, ROLLING_WINDOW, 0.99)

            result = RiskResult(
                tickers=self.tickers,
                weights=self.weights,
                dates=dates,
                portfolio_returns=portfolio_returns,
                corr_matrix=corr_matrix,
                var_table=var_table,
                cvar_table=cvar_table,
                rolling_var_dates=rolling_var_dates,
                rolling_var_95=rolling_var_95,
                rolling_var_99=rolling_var_99,
            )
            self.finished_risk.emit(result)
        except Exception as e:
            self.failed.emit(str(e))