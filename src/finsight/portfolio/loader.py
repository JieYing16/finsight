"""Load portfolio data from CSV or JSON files into a clean DataFrame."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_REQUIRED_COLUMNS = {"ticker", "shares", "purchase_price", "purchase_date"}


def load_portfolio(filepath: str | Path) -> pd.DataFrame:
    """Load a portfolio file and return a validated, typed DataFrame.

    Args:
        filepath: Path to a ``.csv`` or ``.json`` portfolio file.

    Returns:
        DataFrame with columns: ticker (str), shares (float),
        purchase_price (float), purchase_date (datetime).

    Raises:
        FileNotFoundError: If *filepath* does not exist.
        ValueError: If the file format is unsupported or required columns
            are missing.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Portfolio file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = _load_csv(path)
    elif suffix == ".json":
        df = _load_json(path)
    else:
        raise ValueError(f"Unsupported file format: '{suffix}'. Use .csv or .json.")

    _validate_columns(df, path)
    return _coerce_types(df)


def _load_csv(path: Path) -> pd.DataFrame:
    """Read a CSV file into a raw DataFrame."""
    return pd.read_csv(path)


def _load_json(path: Path) -> pd.DataFrame:
    """Read a JSON file into a raw DataFrame.

    Accepts both a JSON array of objects and a dict with a ``"holdings"`` key.
    """
    with path.open() as fh:
        raw = json.load(fh)
    if isinstance(raw, dict) and "holdings" in raw:
        raw = raw["holdings"]
    return pd.DataFrame(raw)


def _validate_columns(df: pd.DataFrame, path: Path) -> None:
    """Raise ValueError if any required columns are absent."""
    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Portfolio file '{path.name}' is missing required columns: {missing}"
        )


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Cast columns to canonical types and strip whitespace from strings."""
    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["shares"] = pd.to_numeric(df["shares"], errors="raise").astype(float)
    df["purchase_price"] = pd.to_numeric(df["purchase_price"], errors="raise").astype(float)
    df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="raise")
    return df.reset_index(drop=True)
