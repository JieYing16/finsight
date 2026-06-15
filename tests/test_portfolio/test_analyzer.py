"""Tests for portfolio.analyzer — risk metrics and diversification."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from finsight.portfolio.analyzer import (
    analyze_portfolio,
    annualized_volatility,
    daily_returns,
    herfindahl_index,
    max_drawdown,
    portfolio_returns,
    sharpe_ratio,
)

_TRADING_DAYS = 252


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def flat_prices() -> pd.DataFrame:
    """Price DataFrame with zero daily movement — volatility must be 0."""
    dates = pd.date_range("2024-01-02", periods=10, freq="B")
    return pd.DataFrame({"AAA": [100.0] * 10, "BBB": [50.0] * 10}, index=dates)


@pytest.fixture()
def trending_prices() -> pd.DataFrame:
    """Prices rising 1% per day — known arithmetic."""
    dates = pd.date_range("2024-01-02", periods=6, freq="B")
    return pd.DataFrame(
        {"AAA": [100.0, 101.0, 102.01, 103.03, 104.06, 105.10]},
        index=dates,
    )


@pytest.fixture()
def drawdown_prices() -> pd.Series:
    """Series with a known 20% drawdown in the middle."""
    return pd.Series([100.0, 110.0, 88.0, 95.0, 105.0])


@pytest.fixture()
def enriched_df() -> pd.DataFrame:
    """Minimal enriched portfolio DataFrame."""
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "weight_pct": [60.0, 40.0],
        }
    )


@pytest.fixture()
def historical_prices() -> pd.DataFrame:
    """30-day historical prices for two tickers with mild noise."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-02", periods=31, freq="B")
    aaa = 100 * np.cumprod(1 + rng.normal(0.0005, 0.01, 31))
    bbb = 50 * np.cumprod(1 + rng.normal(0.0003, 0.008, 31))
    return pd.DataFrame({"AAA": aaa, "BBB": bbb}, index=dates)


# ---------------------------------------------------------------------------
# daily_returns
# ---------------------------------------------------------------------------


def test_daily_returns_shape(trending_prices: pd.DataFrame) -> None:
    ret = daily_returns(trending_prices)
    assert len(ret) == len(trending_prices) - 1


def test_daily_returns_flat(flat_prices: pd.DataFrame) -> None:
    ret = daily_returns(flat_prices)
    assert (ret == 0.0).all().all()


def test_daily_returns_value(trending_prices: pd.DataFrame) -> None:
    ret = daily_returns(trending_prices)
    # Each day rises 1%
    assert ret["AAA"].iloc[0] == pytest.approx(0.01, rel=1e-4)


# ---------------------------------------------------------------------------
# portfolio_returns
# ---------------------------------------------------------------------------


def test_portfolio_returns_equal_weight(flat_prices: pd.DataFrame) -> None:
    ret = daily_returns(flat_prices)
    port = portfolio_returns(ret, {"AAA": 0.5, "BBB": 0.5})
    assert (port == 0.0).all()


def test_portfolio_returns_normalizes_weights(flat_prices: pd.DataFrame) -> None:
    """Unnormalized weights should give same result as normalized."""
    ret = daily_returns(flat_prices)
    p1 = portfolio_returns(ret, {"AAA": 1, "BBB": 1})
    p2 = portfolio_returns(ret, {"AAA": 0.5, "BBB": 0.5})
    pd.testing.assert_series_equal(p1, p2)


def test_portfolio_returns_ignores_missing_ticker(flat_prices: pd.DataFrame) -> None:
    """Tickers not present in returns DataFrame are silently skipped."""
    ret = daily_returns(flat_prices)
    port = portfolio_returns(ret, {"AAA": 0.6, "ZZZ": 0.4})
    assert port is not None  # should not raise


# ---------------------------------------------------------------------------
# annualized_volatility
# ---------------------------------------------------------------------------


def test_annualized_volatility_zero_on_flat(flat_prices: pd.DataFrame) -> None:
    ret = daily_returns(flat_prices)["AAA"]
    assert annualized_volatility(ret) == pytest.approx(0.0, abs=1e-10)


def test_annualized_volatility_formula() -> None:
    """Manual std × √252 should match."""
    daily_vol = 0.01
    rng = np.random.default_rng(0)
    returns = pd.Series(rng.normal(0, daily_vol, 500))
    result = annualized_volatility(returns)
    assert result == pytest.approx(returns.std() * np.sqrt(_TRADING_DAYS), rel=1e-9)


# ---------------------------------------------------------------------------
# sharpe_ratio
# ---------------------------------------------------------------------------


def test_sharpe_zero_when_vol_is_zero(flat_prices: pd.DataFrame) -> None:
    ret = daily_returns(flat_prices)["AAA"]
    assert sharpe_ratio(ret) == 0.0


def test_sharpe_positive_for_strong_trend(trending_prices: pd.DataFrame) -> None:
    ret = daily_returns(trending_prices)["AAA"]
    sr = sharpe_ratio(ret, risk_free_rate=0.0)
    assert sr > 0


def test_sharpe_decreases_with_higher_rf() -> None:
    rng = np.random.default_rng(1)
    returns = pd.Series(rng.normal(0.001, 0.01, 252))
    s_low = sharpe_ratio(returns, risk_free_rate=0.02)
    s_high = sharpe_ratio(returns, risk_free_rate=0.08)
    assert s_low > s_high


# ---------------------------------------------------------------------------
# max_drawdown
# ---------------------------------------------------------------------------


def test_max_drawdown_known_value(drawdown_prices: pd.Series) -> None:
    # Peak is 110, trough is 88: drawdown = (88 - 110) / 110 = -0.2
    dd = max_drawdown(drawdown_prices)
    assert dd == pytest.approx(-0.2, rel=1e-4)


def test_max_drawdown_no_drawdown() -> None:
    prices = pd.Series([100.0, 105.0, 110.0, 115.0])
    assert max_drawdown(prices) == pytest.approx(0.0, abs=1e-10)


def test_max_drawdown_single_element() -> None:
    assert max_drawdown(pd.Series([100.0])) == 0.0


def test_max_drawdown_negative() -> None:
    dd = max_drawdown(pd.Series([100.0, 80.0, 90.0]))
    assert dd < 0


# ---------------------------------------------------------------------------
# herfindahl_index
# ---------------------------------------------------------------------------


def test_hhi_equal_weights_two_assets() -> None:
    # 0.5^2 + 0.5^2 = 0.5
    assert herfindahl_index({"A": 0.5, "B": 0.5}) == pytest.approx(0.5)


def test_hhi_fully_concentrated() -> None:
    assert herfindahl_index({"A": 1.0}) == pytest.approx(1.0)


def test_hhi_lower_for_more_diversified() -> None:
    concentrated = herfindahl_index({"A": 0.8, "B": 0.2})
    diversified = herfindahl_index({"A": 0.5, "B": 0.5})
    assert diversified < concentrated


def test_hhi_normalizes_unnormalized_weights() -> None:
    result = herfindahl_index(pd.Series({"A": 60.0, "B": 40.0}))
    assert result == pytest.approx(0.6**2 + 0.4**2)


def test_hhi_six_equal_holdings() -> None:
    weights = {str(i): 1 / 6 for i in range(6)}
    assert herfindahl_index(weights) == pytest.approx(1 / 6, rel=1e-6)


# ---------------------------------------------------------------------------
# analyze_portfolio
# ---------------------------------------------------------------------------


def test_analyze_portfolio_keys(
    enriched_df: pd.DataFrame, historical_prices: pd.DataFrame
) -> None:
    metrics = analyze_portfolio(enriched_df, historical_prices)
    expected = {"sharpe", "volatility", "max_drawdown", "herfindahl", "n_holdings", "top_holding_weight"}
    assert set(metrics.keys()) == expected


def test_analyze_portfolio_n_holdings(
    enriched_df: pd.DataFrame, historical_prices: pd.DataFrame
) -> None:
    metrics = analyze_portfolio(enriched_df, historical_prices)
    assert metrics["n_holdings"] == 2.0


def test_analyze_portfolio_top_weight(
    enriched_df: pd.DataFrame, historical_prices: pd.DataFrame
) -> None:
    metrics = analyze_portfolio(enriched_df, historical_prices)
    assert metrics["top_holding_weight"] == pytest.approx(60.0)


def test_analyze_portfolio_volatility_positive(
    enriched_df: pd.DataFrame, historical_prices: pd.DataFrame
) -> None:
    metrics = analyze_portfolio(enriched_df, historical_prices)
    assert metrics["volatility"] > 0


def test_analyze_portfolio_max_drawdown_nonpositive(
    enriched_df: pd.DataFrame, historical_prices: pd.DataFrame
) -> None:
    metrics = analyze_portfolio(enriched_df, historical_prices)
    assert metrics["max_drawdown"] <= 0


def test_analyze_portfolio_hhi_in_range(
    enriched_df: pd.DataFrame, historical_prices: pd.DataFrame
) -> None:
    metrics = analyze_portfolio(enriched_df, historical_prices)
    n = int(metrics["n_holdings"])
    assert 1 / n <= metrics["herfindahl"] <= 1.0
