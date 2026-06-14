"""Tests for finsight.market.fetcher."""

# pylint: disable=missing-function-docstring,redefined-outer-name

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from finsight.market.fetcher import (
    enrich_portfolio,
    fetch_current_prices,
    fetch_historical_prices,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _multiindex_df(
    prices: dict[str, float], dates: list[str] | None = None
) -> pd.DataFrame:
    """Return a yfinance-style MultiIndex DataFrame (Close, Ticker)."""
    if dates is None:
        dates = ["2024-01-01"]
    tickers = list(prices.keys())
    index = pd.DatetimeIndex(dates)
    cols = pd.MultiIndex.from_arrays([["Close"] * len(tickers), tickers])
    data = [[prices[t] for t in tickers] for _ in dates]
    return pd.DataFrame(data, index=index, columns=cols)


def _flat_df(
    ticker: str, prices: list[float], dates: list[str] | None = None
) -> pd.DataFrame:
    """Return a yfinance-style flat-column DataFrame for a single ticker."""
    if dates is None:
        dates = ["2024-01-01"]
    return pd.DataFrame({"Close": prices}, index=pd.DatetimeIndex(dates))


def _sample_portfolio() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["VTI", "BND"],
            "shares": [50.0, 30.0],
            "purchase_price": [180.0, 80.0],
            "purchase_date": pd.to_datetime(["2022-01-15", "2022-01-15"]),
        }
    )


# ---------------------------------------------------------------------------
# fetch_current_prices
# ---------------------------------------------------------------------------


def test_fetch_current_prices_multiindex() -> None:
    mock_data = _multiindex_df({"VTI": 220.0, "BND": 85.0})
    with patch("finsight.market.fetcher.yf.download", return_value=mock_data):
        result = fetch_current_prices(["VTI", "BND"])
    assert result == {"VTI": 220.0, "BND": 85.0}


def test_fetch_current_prices_flat_columns() -> None:
    mock_data = _flat_df("VTI", [220.0])
    with patch("finsight.market.fetcher.yf.download", return_value=mock_data):
        result = fetch_current_prices(["VTI"])
    assert result == {"VTI": 220.0}


def test_fetch_current_prices_uses_latest_row() -> None:
    mock_data = _multiindex_df({"VTI": 200.0}, dates=["2024-01-01"])
    # Append a newer date with a different price
    newer = _multiindex_df({"VTI": 225.0}, dates=["2024-01-02"])
    combined = pd.concat([mock_data, newer])
    with patch("finsight.market.fetcher.yf.download", return_value=combined):
        result = fetch_current_prices(["VTI"])
    assert result["VTI"] == pytest.approx(225.0)


def test_fetch_current_prices_empty_list() -> None:
    result = fetch_current_prices([])
    assert result == {}


def test_fetch_current_prices_no_data_raises() -> None:
    # All NaN → dropna(how="all") empties the DataFrame → ValueError
    mock_data = _multiindex_df({"VTI": float("nan")})
    with patch("finsight.market.fetcher.yf.download", return_value=mock_data):
        with pytest.raises(ValueError, match="No price data"):
            fetch_current_prices(["VTI"])


# ---------------------------------------------------------------------------
# fetch_historical_prices
# ---------------------------------------------------------------------------


def test_fetch_historical_prices_returns_dataframe() -> None:
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    mock_data = _multiindex_df({"VTI": 210.0, "BND": 83.0}, dates=dates)
    with patch("finsight.market.fetcher.yf.download", return_value=mock_data):
        result = fetch_historical_prices(["VTI", "BND"], "2024-01-01", "2024-01-03")
    assert isinstance(result, pd.DataFrame)
    assert set(result.columns) == {"VTI", "BND"}
    assert len(result) == 3


def test_fetch_historical_prices_empty_tickers() -> None:
    result = fetch_historical_prices([], "2024-01-01", "2024-01-31")
    assert result.empty


def test_fetch_historical_prices_passes_dates_to_yfinance() -> None:
    mock_data = _multiindex_df({"VTI": 210.0}, dates=["2024-06-01"])
    patch_target = "finsight.market.fetcher.yf.download"
    with patch(patch_target, return_value=mock_data) as mock_dl:
        fetch_historical_prices(["VTI"], "2024-06-01", "2024-06-30")
    call_kwargs = mock_dl.call_args.kwargs
    assert call_kwargs["start"] == "2024-06-01"
    assert call_kwargs["end"] == "2024-06-30"


# ---------------------------------------------------------------------------
# enrich_portfolio
# ---------------------------------------------------------------------------


def test_enrich_portfolio_adds_expected_columns() -> None:
    df = _sample_portfolio()
    mock_data = _multiindex_df({"VTI": 220.0, "BND": 85.0})
    with patch("finsight.market.fetcher.yf.download", return_value=mock_data):
        result = enrich_portfolio(df)
    assert set(result.columns) >= {
        "current_price",
        "market_value",
        "cost_basis",
        "gain_loss",
        "gain_loss_pct",
        "weight_pct",
    }


def test_enrich_portfolio_market_value() -> None:
    df = _sample_portfolio()
    mock_data = _multiindex_df({"VTI": 220.0, "BND": 85.0})
    with patch("finsight.market.fetcher.yf.download", return_value=mock_data):
        result = enrich_portfolio(df)
    vti = result.loc[result["ticker"] == "VTI"].iloc[0]
    bnd = result.loc[result["ticker"] == "BND"].iloc[0]
    assert vti["market_value"] == pytest.approx(50 * 220.0)
    assert bnd["market_value"] == pytest.approx(30 * 85.0)


def test_enrich_portfolio_gain_loss() -> None:
    df = _sample_portfolio()
    mock_data = _multiindex_df({"VTI": 220.0, "BND": 85.0})
    with patch("finsight.market.fetcher.yf.download", return_value=mock_data):
        result = enrich_portfolio(df)
    vti = result.loc[result["ticker"] == "VTI"].iloc[0]
    # cost basis = 50 * 180 = 9000; market value = 50 * 220 = 11000
    assert vti["gain_loss"] == pytest.approx(2000.0)
    assert vti["gain_loss_pct"] == pytest.approx(2000.0 / 9000.0 * 100, abs=0.01)


def test_enrich_portfolio_weights_sum_to_100() -> None:
    df = _sample_portfolio()
    mock_data = _multiindex_df({"VTI": 220.0, "BND": 85.0})
    with patch("finsight.market.fetcher.yf.download", return_value=mock_data):
        result = enrich_portfolio(df)
    assert result["weight_pct"].sum() == pytest.approx(100.0, abs=0.01)


def test_enrich_portfolio_does_not_mutate_input() -> None:
    df = _sample_portfolio()
    original_columns = set(df.columns)
    mock_data = _multiindex_df({"VTI": 220.0, "BND": 85.0})
    with patch("finsight.market.fetcher.yf.download", return_value=mock_data):
        enrich_portfolio(df)
    assert set(df.columns) == original_columns
