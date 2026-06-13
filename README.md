# FinSight

A data-driven personal financial advisor agent built in Python.

FinSight goes beyond generic budgeting tools by applying real forecasting and analytical techniques — Monte Carlo simulation, ARIMA/Prophet time series models, macro-economic indicators — to help everyday investors make informed portfolio decisions.

> **Disclaimer:** This is for educational and informational purposes only. Not financial advice. Consult a licensed financial advisor for personalized guidance.

---

## Features (Phase 1)

- Load portfolios from CSV or JSON
- Portfolio summary with cost-basis weights
- Clean, typed DataFrame output for downstream analysis

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Portfolio loader, CLI, analyzer | In progress |
| 2 | Forecasting (Prophet/ARIMA), macro indicators, scenario analysis | Planned |
| 3 | FastAPI backend, Streamlit dashboard, deployment | Planned |

---

## Installation

Requires Python 3.10+.

```bash
# Clone
git clone https://github.com/your-username/finsight.git
cd finsight

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

---

## Usage

### Load a portfolio

```bash
finsight load data/sample_portfolio.csv
```

Example output:

```
               Portfolio — sample_portfolio.csv
┏━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Ticker ┃ Shares ┃ Purchase Price ┃ Purchase Date ┃ Market Value   ┃ Weight % ┃
┡━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ VTI    │  50.00 │       $180.25  │  2022-01-15   │    $9,012.50   │  36.08%  │
│ ...    │   ...  │          ...   │      ...      │         ...    │    ...   │
└────────┴────────┴────────────────┴───────────────┴────────────────┴──────────┘

Total portfolio value (at cost): $24,980.25
Holdings: 6
```

### JSON portfolio format

```json
[
  {"ticker": "VTI", "shares": 50, "purchase_price": 180.25, "purchase_date": "2022-01-15"},
  {"ticker": "BND", "shares": 30, "purchase_price": 82.10,  "purchase_date": "2022-01-15"}
]
```

Or with a wrapper key:

```json
{
  "name": "My Portfolio",
  "holdings": [...]
}
```

---

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=finsight --cov-report=term-missing

# Lint and format
ruff check src tests
ruff format src tests
```

### Project layout

```
src/finsight/
├── cli.py              # CLI entry point (typer)
├── portfolio/
│   ├── loader.py       # CSV/JSON → DataFrame
│   ├── analyzer.py     # Sharpe, volatility, drawdown (Phase 1)
│   ├── rebalancer.py   # Rebalancing suggestions (Phase 1)
│   └── optimizer.py    # Mean-variance optimization (Phase 1)
├── market/             # yfinance + FRED (Phase 2)
├── forecast/           # Prophet/ARIMA, Monte Carlo (Phase 2)
├── advisor/            # Risk profile + LLM insights (Phase 2)
└── utils/              # Config, formatting
```

---

## Contributing

Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`

Every feature lives on a branch and merges via PR with tests.

### Note on `CLAUDE.md`

This repo includes a `CLAUDE.md` file with project context, architecture, and
coding standards for AI coding assistants. It's the same idea as a
`CONTRIBUTING.md` aimed at an AI pair-programmer — it doesn't affect the
runtime app and isn't required reading for human contributors, though it's a
useful overview of project conventions.
