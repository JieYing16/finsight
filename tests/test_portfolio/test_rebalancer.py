"""Tests for portfolio.rebalancer — target-weight drift and trade suggestions."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from finsight.portfolio.rebalancer import (
    compute_rebalance,
    equal_weights,
    validate_target_weights,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def balanced_portfolio() -> pd.DataFrame:
    """Two holdings exactly at a 60/40 split with known prices."""
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "current_price": [100.0, 50.0],
            "market_value": [600.0, 400.0],
        }
    )


@pytest.fixture()
def drifted_portfolio() -> pd.DataFrame:
    """AAA has drifted overweight relative to a 50/50 target."""
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "current_price": [100.0, 50.0],
            "market_value": [800.0, 200.0],
        }
    )


# ---------------------------------------------------------------------------
# equal_weights
# ---------------------------------------------------------------------------


def test_equal_weights_two_tickers() -> None:
    assert equal_weights(["AAA", "BBB"]) == {"AAA": 0.5, "BBB": 0.5}


def test_equal_weights_empty() -> None:
    assert equal_weights([]) == {}


def test_equal_weights_sums_to_one() -> None:
    weights = equal_weights(["A", "B", "C", "D", "E"])
    assert sum(weights.values()) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# validate_target_weights
# ---------------------------------------------------------------------------


def test_validate_accepts_valid_weights() -> None:
    validate_target_weights({"A": 0.6, "B": 0.4})  # should not raise


def test_validate_rejects_negative_weight() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        validate_target_weights({"A": -0.1, "B": 1.1})


def test_validate_rejects_weights_not_summing_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_target_weights({"A": 0.5, "B": 0.2})


def test_validate_tolerates_rounding_error() -> None:
    validate_target_weights({"A": 0.333, "B": 0.333, "B2": 0.334})  # ~1.0


# ---------------------------------------------------------------------------
# compute_rebalance — balanced portfolio (no drift)
# ---------------------------------------------------------------------------


def test_compute_rebalance_no_drift_all_hold(balanced_portfolio: pd.DataFrame) -> None:
    result = compute_rebalance(balanced_portfolio, {"AAA": 0.6, "BBB": 0.4})
    assert (result["action"] == "hold").all()
    assert (result["trade_value"] == 0.0).all()


def test_compute_rebalance_weights_match_target(
    balanced_portfolio: pd.DataFrame,
) -> None:
    result = compute_rebalance(balanced_portfolio, {"AAA": 0.6, "BBB": 0.4})
    row = result.set_index("ticker")
    assert row.loc["AAA", "current_weight_pct"] == pytest.approx(60.0)
    assert row.loc["AAA", "target_weight_pct"] == pytest.approx(60.0)


# ---------------------------------------------------------------------------
# compute_rebalance — drifted portfolio
# ---------------------------------------------------------------------------


def test_compute_rebalance_sell_overweight(drifted_portfolio: pd.DataFrame) -> None:
    result = compute_rebalance(drifted_portfolio, {"AAA": 0.5, "BBB": 0.5})
    row = result.set_index("ticker")
    assert row.loc["AAA", "action"] == "sell"
    assert row.loc["AAA", "trade_value"] < 0


def test_compute_rebalance_buy_underweight(drifted_portfolio: pd.DataFrame) -> None:
    result = compute_rebalance(drifted_portfolio, {"AAA": 0.5, "BBB": 0.5})
    row = result.set_index("ticker")
    assert row.loc["BBB", "action"] == "buy"
    assert row.loc["BBB", "trade_value"] > 0


def test_compute_rebalance_trade_values_net_to_zero(
    drifted_portfolio: pd.DataFrame,
) -> None:
    """Buys and sells should offset — no net cash in or out."""
    result = compute_rebalance(drifted_portfolio, {"AAA": 0.5, "BBB": 0.5})
    assert result["trade_value"].sum() == pytest.approx(0.0, abs=1e-6)


def test_compute_rebalance_shares_consistent_with_trade_value(
    drifted_portfolio: pd.DataFrame,
) -> None:
    result = compute_rebalance(drifted_portfolio, {"AAA": 0.5, "BBB": 0.5})
    row = result.set_index("ticker")
    bbb_price = 50.0
    assert row.loc["BBB", "shares"] * bbb_price == pytest.approx(
        row.loc["BBB", "trade_value"], abs=1e-2
    )


# ---------------------------------------------------------------------------
# compute_rebalance — threshold
# ---------------------------------------------------------------------------


def test_compute_rebalance_within_threshold_holds(
    drifted_portfolio: pd.DataFrame,
) -> None:
    """A large threshold should suppress trade suggestions entirely."""
    result = compute_rebalance(
        drifted_portfolio, {"AAA": 0.5, "BBB": 0.5}, threshold_pct=50.0
    )
    assert (result["action"] == "hold").all()


def test_compute_rebalance_threshold_zero_flags_any_drift(
    drifted_portfolio: pd.DataFrame,
) -> None:
    result = compute_rebalance(
        drifted_portfolio, {"AAA": 0.5, "BBB": 0.5}, threshold_pct=0.0
    )
    assert (result["action"] != "hold").any()


# ---------------------------------------------------------------------------
# compute_rebalance — new / dropped tickers
# ---------------------------------------------------------------------------


def test_compute_rebalance_new_ticker_is_buy(balanced_portfolio: pd.DataFrame) -> None:
    """A target ticker not currently held should appear as a buy."""
    result = compute_rebalance(
        balanced_portfolio, {"AAA": 0.4, "BBB": 0.3, "CCC": 0.3}
    )
    row = result.set_index("ticker")
    assert "CCC" in row.index
    assert row.loc["CCC", "action"] == "buy"
    assert row.loc["CCC", "current_value"] == 0.0


def test_compute_rebalance_dropped_ticker_is_full_sell(
    balanced_portfolio: pd.DataFrame,
) -> None:
    """A held ticker absent from target weights should be sold to zero."""
    result = compute_rebalance(balanced_portfolio, {"AAA": 1.0})
    row = result.set_index("ticker")
    assert row.loc["BBB", "action"] == "sell"
    assert row.loc["BBB", "target_value"] == 0.0


def test_compute_rebalance_new_ticker_shares_nan_without_price(
    balanced_portfolio: pd.DataFrame,
) -> None:
    """New tickers have no known price, so shares should be NaN."""
    result = compute_rebalance(
        balanced_portfolio, {"AAA": 0.4, "BBB": 0.3, "CCC": 0.3}
    )
    row = result.set_index("ticker")
    assert math.isnan(row.loc["CCC", "shares"])


# ---------------------------------------------------------------------------
# compute_rebalance — invalid weights propagate
# ---------------------------------------------------------------------------


def test_compute_rebalance_raises_on_invalid_weights(
    balanced_portfolio: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        compute_rebalance(balanced_portfolio, {"AAA": 0.5, "BBB": 0.1})
