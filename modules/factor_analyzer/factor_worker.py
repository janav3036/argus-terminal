from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf
from PySide6.QtCore import QThread, Signal

from modules.rates.rates_bridge import load_cached_yields

UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "ASIANPAINT.NS",
]
MARKET_TICKER = "^NSEI"
LOOKBACK_PERIOD = "3y"
MOM_LOOKBACK_DAYS = 252
MOM_SKIP_DAYS = 21
ROLLING_WINDOW = 60
FACTOR_NAMES = ["Mkt-RF", "SMB", "HML", "MOM"]


@dataclass
class FactorResult:
    factors: pd.DataFrame
    portfolio_returns: pd.Series
    coefficients: dict
    tstats: dict
    r_squared: float
    rolling_betas: pd.DataFrame
    rolling_alpha: pd.Series


def _fetch_close(ticker: str) -> pd.Series:
    bars = yf.Ticker(ticker).history(period=LOOKBACK_PERIOD, interval="1d")
    if bars.empty:
        raise ValueError(f"No price data found for '{ticker}' - check the ticker symbol")
    close = bars["Close"]
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    return close


def _fetch_universe_prices() -> pd.DataFrame:
    prices = {ticker: _fetch_close(ticker) for ticker in UNIVERSE}
    return pd.DataFrame(prices).dropna()


def _fetch_universe_fundamentals() -> dict:
    fundamentals = {}
    for ticker in UNIVERSE:
        info = yf.Ticker(ticker).info
        market_cap = info.get("marketCap")
        book_value = info.get("bookValue")
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not market_cap or not book_value or not price:
            raise ValueError(f"Missing fundamentals for universe ticker '{ticker}'")
        fundamentals[ticker] = {
            "market_cap": market_cap,
            "book_to_market": book_value / price,
        }
    return fundamentals


def _build_smb_hml(returns: pd.DataFrame, fundamentals: dict) -> tuple[pd.Series, pd.Series]:
    caps = pd.Series({t: fundamentals[t]["market_cap"] for t in returns.columns})
    book_to_markets = pd.Series({t: fundamentals[t]["book_to_market"] for t in returns.columns})

    cap_median = caps.median()
    small = caps[caps <= cap_median].index
    big = caps[caps > cap_median].index
    smb = returns[small].mean(axis=1) - returns[big].mean(axis=1)

    bm_median = book_to_markets.median()
    high = book_to_markets[book_to_markets >= bm_median].index
    low = book_to_markets[book_to_markets < bm_median].index
    hml = returns[high].mean(axis=1) - returns[low].mean(axis=1)

    return smb, hml


def _build_momentum(prices: pd.DataFrame, returns: pd.DataFrame) -> pd.Series:
    momentum_score = prices.shift(MOM_SKIP_DAYS) / prices.shift(MOM_LOOKBACK_DAYS) - 1

    mom = pd.Series(index=returns.index, dtype=float)
    for date in returns.index:
        scores = momentum_score.loc[date].dropna()
        if len(scores) < 4:
            continue
        median = scores.median()
        winners = scores[scores >= median].index
        losers = scores[scores < median].index
        mom.loc[date] = returns.loc[date, winners].mean() - returns.loc[date, losers].mean()

    return mom


def _build_market_factor(trading_dates: pd.DatetimeIndex) -> pd.Series:
    market_returns = _fetch_close(MARKET_TICKER).pct_change().dropna()

    gsec = load_cached_yields()[["date", "tenor_3m"]].copy()
    gsec["date"] = pd.to_datetime(gsec["date"]).dt.normalize().astype("datetime64[ns]")

    dates_df = pd.DataFrame({"date": trading_dates.astype("datetime64[ns]")}).sort_values("date")
    merged = pd.merge_asof(dates_df, gsec.sort_values("date"), on="date", direction="backward")
    rf_daily = merged.set_index("date")["tenor_3m"] / 252

    return (market_returns - rf_daily).dropna()


def _build_factors() -> pd.DataFrame:
    prices = _fetch_universe_prices()
    fundamentals = _fetch_universe_fundamentals()
    returns = prices.pct_change().dropna()

    smb, hml = _build_smb_hml(returns, fundamentals)
    mom = _build_momentum(prices, returns)
    mkt_rf = _build_market_factor(returns.index)

    factors = pd.DataFrame({"Mkt-RF": mkt_rf, "SMB": smb, "HML": hml, "MOM": mom}).dropna()
    return factors


def _fetch_portfolio_returns(tickers: list[str], weights: np.ndarray) -> pd.Series:
    prices = {ticker: _fetch_close(ticker) for ticker in tickers}
    price_df = pd.DataFrame(prices).dropna()
    returns_df = price_df.pct_change().dropna()
    return pd.Series(returns_df.to_numpy() @ weights, index=returns_df.index)


def _rolling_regression(portfolio_returns: pd.Series, factors: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    n = len(portfolio_returns)
    dates, alphas, beta_rows = [], [], []
    for end in range(ROLLING_WINDOW, n + 1):
        window = portfolio_returns.index[end - ROLLING_WINDOW:end]
        y_window = portfolio_returns.loc[window]
        X_window = sm.add_constant(factors.loc[window, FACTOR_NAMES])
        fit = sm.OLS(y_window, X_window).fit()
        dates.append(window[-1])
        alphas.append(fit.params["const"])
        beta_rows.append(fit.params[FACTOR_NAMES].to_dict())

    index = pd.Index(dates, name="date")
    return pd.DataFrame(beta_rows, index=index), pd.Series(alphas, index=index)


class FactorWorker(QThread):
    finished_factors = Signal(object)
    failed = Signal(str)

    def __init__(self, tickers: list[str], weights: np.ndarray, parent=None):
        super().__init__(parent)
        self.tickers = tickers
        self.weights = weights

    def run(self):
        try:
            factors = _build_factors()
            portfolio_returns = _fetch_portfolio_returns(self.tickers, self.weights)

            common_index = factors.index.intersection(portfolio_returns.index).sort_values()
            if len(common_index) < ROLLING_WINDOW:
                raise ValueError("Not enough overlapping history between the portfolio and factor data")
            factors = factors.loc[common_index]
            portfolio_returns = portfolio_returns.loc[common_index]

            X = sm.add_constant(factors[FACTOR_NAMES])
            fit = sm.OLS(portfolio_returns, X).fit()

            rolling_betas, rolling_alpha = _rolling_regression(portfolio_returns, factors)

            result = FactorResult(
                factors=factors,
                portfolio_returns=portfolio_returns,
                coefficients=dict(fit.params),
                tstats=dict(fit.tvalues),
                r_squared=fit.rsquared,
                rolling_betas=rolling_betas,
                rolling_alpha=rolling_alpha,
            )
            self.finished_factors.emit(result)
        except Exception as e:
            self.failed.emit(str(e))