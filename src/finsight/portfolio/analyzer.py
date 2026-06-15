"""Portfolio risk metrics and diversification analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd

_TRADING_DAYS = 252


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute daily percentage returns from a close-price DataFrame.

    Parameters
    ----------
    prices : pd.DataFrame
        Close prices indexed by date, one column per ticker.

    Returns
    -------
    pd.DataFrame
        Daily returns with the first row dropped.
    """
    return prices.pct_change().dropna()


def portfolio_returns(
    returns: pd.DataFrame,
    weights: dict[str, float],
) -> pd.Series:
    """Compute weighted daily portfolio returns.

    Parameters
    ----------
    returns : pd.DataFrame
        Daily returns indexed by date, one column per ticker.
    weights : dict[str, float]
        Ticker → weight mapping. Weights are normalized internally so they
        need not sum to exactly 1.

    Returns
    -------
    pd.Series
        Weighted daily portfolio returns indexed by date.
    """
    tickers = [t for t in weights if t in returns.columns]
    w = np.array([weights[t] for t in tickers], dtype=float)
    w /= w.sum()
    return returns[tickers].dot(w)


def annualized_volatility(returns: pd.Series) -> float:
    """Annualized volatility (std dev of daily returns × √252).

    Parameters
    ----------
    returns : pd.Series
        Daily returns series.

    Returns
    -------
    float
        Annualized volatility as a decimal (e.g. 0.18 = 18%).
    """
    return float(returns.std() * np.sqrt(_TRADING_DAYS))


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
    """Annualized Sharpe ratio.

    Parameters
    ----------
    returns : pd.Series
        Daily portfolio returns.
    risk_free_rate : float
        Annual risk-free rate as a decimal (default 0.05 = 5%).

    Returns
    -------
    float
        Sharpe ratio. Returns 0.0 if volatility is zero.
    """
    annual_return = float(returns.mean() * _TRADING_DAYS)
    vol = annualized_volatility(returns)
    if vol == 0.0:
        return 0.0
    return (annual_return - risk_free_rate) / vol


def max_drawdown(prices: pd.Series) -> float:
    """Maximum peak-to-trough drawdown from a price (or NAV) series.

    Parameters
    ----------
    prices : pd.Series
        Time series of prices or cumulative portfolio values.

    Returns
    -------
    float
        Maximum drawdown as a negative decimal (e.g. -0.35 = -35%).
        Returns 0.0 for a series with a single element.
    """
    if len(prices) < 2:
        return 0.0
    roll_max = prices.cummax()
    drawdown = (prices - roll_max) / roll_max
    return float(drawdown.min())


def herfindahl_index(weights: pd.Series | dict[str, float]) -> float:
    """Herfindahl–Hirschman Index (HHI) as a portfolio concentration score.

    Lower HHI = better diversification.
    Ranges from 1/N (equal weight) to 1.0 (single holding).

    Parameters
    ----------
    weights : pd.Series or dict
        Portfolio weights. Normalized internally.

    Returns
    -------
    float
        HHI in [1/N, 1.0].
    """
    w = pd.Series(weights) if isinstance(weights, dict) else weights.copy()
    w = w / w.sum()
    return float((w**2).sum())


def analyze_portfolio(
    enriched_df: pd.DataFrame,
    historical_prices: pd.DataFrame,
    risk_free_rate: float = 0.05,
) -> dict[str, float]:
    """Compute portfolio-level risk metrics and diversification score.

    Parameters
    ----------
    enriched_df : pd.DataFrame
        Enriched portfolio from :func:`~finsight.market.fetcher.enrich_portfolio`.
        Must contain: ticker, weight_pct.
    historical_prices : pd.DataFrame
        Daily close prices indexed by date, one column per ticker.
        From :func:`~finsight.market.fetcher.fetch_historical_prices`.
    risk_free_rate : float
        Annual risk-free rate as a decimal (default 0.05 = 5%).

    Returns
    -------
    dict[str, float]
        Keys: sharpe, volatility, max_drawdown, herfindahl, n_holdings,
        top_holding_weight.
    """
    weights = dict(zip(enriched_df["ticker"], enriched_df["weight_pct"] / 100))

    port_ret = portfolio_returns(daily_returns(historical_prices), weights)
    port_nav = (1 + port_ret).cumprod()

    return {
        "sharpe": sharpe_ratio(port_ret, risk_free_rate),
        "volatility": annualized_volatility(port_ret),
        "max_drawdown": max_drawdown(port_nav),
        "herfindahl": herfindahl_index(pd.Series(weights)),
        "n_holdings": float(len(enriched_df)),
        "top_holding_weight": float(enriched_df["weight_pct"].max()),
    }
