"""Tests for finsight.portfolio.loader."""

# pylint: disable=missing-function-docstring,redefined-outer-name

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pandas as pd
import pytest

from finsight.portfolio.loader import load_portfolio

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def csv_file(tmp_path: Path) -> Path:
    p = tmp_path / "portfolio.csv"
    p.write_text(
        textwrap.dedent("""\
            ticker,shares,purchase_price,purchase_date
            VTI,50,180.25,2022-01-15
            BND,30,82.10,2022-01-15
            QQQ,15,285.50,2023-03-10
        """)
    )
    return p


@pytest.fixture()
def json_array_file(tmp_path: Path) -> Path:
    p = tmp_path / "portfolio.json"
    data = [
        {
            "ticker": "VTI",
            "shares": 50,
            "purchase_price": 180.25,
            "purchase_date": "2022-01-15",
        },
        {
            "ticker": "BND",
            "shares": 30,
            "purchase_price": 82.10,
            "purchase_date": "2022-01-15",
        },
    ]
    p.write_text(json.dumps(data))
    return p


@pytest.fixture()
def json_holdings_file(tmp_path: Path) -> Path:
    p = tmp_path / "portfolio.json"
    data = {
        "name": "My Portfolio",
        "holdings": [
            {
                "ticker": "VTI",
                "shares": 50,
                "purchase_price": 180.25,
                "purchase_date": "2022-01-15",
            },
        ],
    }
    p.write_text(json.dumps(data))
    return p


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_load_csv_returns_dataframe(csv_file: Path) -> None:
    df = load_portfolio(csv_file)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3


def test_load_csv_column_types(csv_file: Path) -> None:
    df = load_portfolio(csv_file)
    assert pd.api.types.is_string_dtype(df["ticker"])
    assert pd.api.types.is_float_dtype(df["shares"])
    assert pd.api.types.is_float_dtype(df["purchase_price"])
    assert pd.api.types.is_datetime64_any_dtype(df["purchase_date"])


def test_load_csv_ticker_uppercased(tmp_path: Path) -> None:
    p = tmp_path / "p.csv"
    p.write_text(
        "ticker,shares,purchase_price,purchase_date\nvti,10,100.0,2023-01-01\n"
    )
    df = load_portfolio(p)
    assert df["ticker"].iloc[0] == "VTI"


def test_load_json_array(json_array_file: Path) -> None:
    df = load_portfolio(json_array_file)
    assert len(df) == 2
    assert set(df.columns) >= {"ticker", "shares", "purchase_price", "purchase_date"}


def test_load_json_holdings_key(json_holdings_file: Path) -> None:
    df = load_portfolio(json_holdings_file)
    assert len(df) == 1
    assert df["ticker"].iloc[0] == "VTI"


def test_index_is_reset(csv_file: Path) -> None:
    df = load_portfolio(csv_file)
    assert list(df.index) == list(range(len(df)))


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        load_portfolio(tmp_path / "nonexistent.csv")


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    p = tmp_path / "data.xlsx"
    p.write_text("dummy")
    with pytest.raises(ValueError, match="Unsupported file format"):
        load_portfolio(p)


def test_missing_columns_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.csv"
    p.write_text("ticker,shares\nVTI,10\n")
    with pytest.raises(ValueError, match="missing required columns"):
        load_portfolio(p)


def test_invalid_numeric_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.csv"
    p.write_text("ticker,shares,purchase_price,purchase_date\nVTI,abc,100,2023-01-01\n")
    with pytest.raises(Exception):  # pandas ValueError
        load_portfolio(p)
