"""Market price data via yfinance."""

from __future__ import annotations

from datetime import date

import pandas as pd
import yfinance as yf


def fetch_current_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch the latest closing price for each ticker.

    Parameters
    ----------
    tickers : list[str]
        List of ticker symbols (e.g. ["VTI", "BND"]).

    Returns
    -------
    dict[str, float]
        Mapping of ticker → most recent closing price.

    Raises
    ------
    ValueError
        If no price data is returned for any ticker.
    """
    if not tickers:
        return {}

    raw = yf.download(tickers, period="5d", auto_adjust=True, progress=False)
    close = _extract_close(raw, tickers)

    if close.empty:
        raise ValueError(f"No price data returned for tickers: {tickers}")

    prices: dict[str, float] = {}
    for ticker in tickers:
        if ticker not in close.columns:
            continue
        series = close[ticker].dropna()
        if series.empty:
            continue
        prices[ticker] = float(series.iloc[-1])

    if not prices:
        raise ValueError(f"No price data returned for tickers: {tickers}")

    return prices


def fetch_historical_prices(
    tickers: list[str],
    start: str | date,
    end: str | date,
) -> pd.DataFrame:
    """Fetch daily closing prices for a date range.

    Parameters
    ----------
    tickers : list[str]
        List of ticker symbols.
    start : str or datetime.date
        Start date (inclusive).
    end : str or datetime.date
        End date (inclusive).

    Returns
    -------
    pd.DataFrame
        Indexed by date with one column per ticker (close prices).
    """
    if not tickers:
        return pd.DataFrame()

    raw = yf.download(
        tickers, start=str(start), end=str(end), auto_adjust=True, progress=False
    )
    return _extract_close(raw, tickers)


def enrich_portfolio(df: pd.DataFrame) -> pd.DataFrame:
    """Add live market columns to a portfolio DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Portfolio DataFrame from :func:`~finsight.portfolio.loader.load_portfolio`.
        Must contain: ticker, shares, purchase_price.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with added columns: current_price, market_value, cost_basis,
        gain_loss, gain_loss_pct, weight_pct.
    """
    tickers = df["ticker"].tolist()
    prices = fetch_current_prices(tickers)

    out = df.copy()
    out["current_price"] = out["ticker"].map(prices)
    out["market_value"] = out["shares"] * out["current_price"]
    out["cost_basis"] = out["shares"] * out["purchase_price"]
    out["gain_loss"] = out["market_value"] - out["cost_basis"]
    out["gain_loss_pct"] = (out["gain_loss"] / out["cost_basis"] * 100).round(2)

    total_value = out["market_value"].sum()
    out["weight_pct"] = (out["market_value"] / total_value * 100).round(2)

    return out


def _extract_close(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Return a per-ticker Close DataFrame from a yfinance download result."""
    if isinstance(raw.columns, pd.MultiIndex):
        return raw["Close"].dropna(how="all")
    # Flat columns: single-ticker download on older yfinance
    return raw[["Close"]].rename(columns={"Close": tickers[0]}).dropna(how="all")
