"""Portfolio rebalancing — target-weight drift and trade suggestions."""

from __future__ import annotations

import pandas as pd


def equal_weights(tickers: list[str]) -> dict[str, float]:
    """Equal-weight target allocation across all tickers.

    Parameters
    ----------
    tickers : list[str]
        Ticker symbols.

    Returns
    -------
    dict[str, float]
        Ticker → weight (fractions summing to 1.0). Empty dict if
        *tickers* is empty.
    """
    n = len(tickers)
    return {t: 1 / n for t in tickers} if n else {}


def validate_target_weights(weights: dict[str, float]) -> None:
    """Validate that target weights are non-negative and sum to ~1.0.

    Parameters
    ----------
    weights : dict[str, float]
        Ticker → target weight.

    Raises
    ------
    ValueError
        If any weight is negative, or the weights do not sum to 1.0
        within a 1% tolerance.
    """
    if any(w < 0 for w in weights.values()):
        raise ValueError("Target weights must be non-negative.")
    total = sum(weights.values())
    if not 0.99 <= total <= 1.01:
        raise ValueError(f"Target weights must sum to 1.0 (got {total:.4f}).")


def compute_rebalance(
    enriched_df: pd.DataFrame,
    target_weights: dict[str, float],
    threshold_pct: float = 0.0,
) -> pd.DataFrame:
    """Compute weight drift and suggested trades to reach target weights.

    Parameters
    ----------
    enriched_df : pd.DataFrame
        Enriched portfolio from :func:`~finsight.market.fetcher.enrich_portfolio`.
        Must contain: ticker, current_price, market_value.
    target_weights : dict[str, float]
        Ticker → target weight (fractions summing to ~1.0). Tickers with a
        positive target weight that are not currently held are included as
        new buy suggestions; tickers held but absent from *target_weights*
        are treated as a 0% target (full sell).
    threshold_pct : float
        Minimum absolute drift (in percentage points) required to suggest
        a trade. Holdings within this threshold are marked "hold" with a
        zero trade value. Default 0.0 — suggest a trade for any drift.

    Returns
    -------
    pd.DataFrame
        Columns: ticker, current_weight_pct, target_weight_pct, drift_pct,
        current_value, target_value, trade_value, action, shares.
        ``action`` is one of "buy", "sell", "hold". ``shares`` is the
        approximate number of shares implied by trade_value, or NaN if the
        ticker has no known current price. Sorted by drift, largest
        overweight first.

    Raises
    ------
    ValueError
        If *target_weights* are invalid (see :func:`validate_target_weights`).
    """
    validate_target_weights(target_weights)

    total_value = enriched_df["market_value"].sum()
    current_values = dict(zip(enriched_df["ticker"], enriched_df["market_value"]))
    prices = dict(zip(enriched_df["ticker"], enriched_df["current_price"]))

    all_tickers = sorted(set(current_values) | set(target_weights))
    rows = []
    for ticker in all_tickers:
        current_value = current_values.get(ticker, 0.0)
        target_weight = target_weights.get(ticker, 0.0)
        current_weight = current_value / total_value if total_value else 0.0
        target_value = target_weight * total_value
        drift_pct = (current_weight - target_weight) * 100
        trade_value = target_value - current_value

        if abs(drift_pct) <= threshold_pct:
            action = "hold"
            trade_value = 0.0
        elif trade_value > 0:
            action = "buy"
        else:
            action = "sell"

        price = prices.get(ticker)
        shares = trade_value / price if price else float("nan")

        rows.append(
            {
                "ticker": ticker,
                "current_weight_pct": round(current_weight * 100, 2),
                "target_weight_pct": round(target_weight * 100, 2),
                "drift_pct": round(drift_pct, 2),
                "current_value": round(current_value, 2),
                "target_value": round(target_value, 2),
                "trade_value": round(trade_value, 2),
                "action": action,
                "shares": round(shares, 4),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("drift_pct", ascending=False)
        .reset_index(drop=True)
    )
