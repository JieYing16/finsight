# FinSight — Personal Financial Advisor Agent

## Project Overview

A Python-based personal financial advisor agent built by a data scientist with professional experience in demand forecasting (Western Digital) and financial KPI forecasting (Shell). This project leverages real forecasting and analytical skills to go beyond generic budgeting tools.

The agent helps everyday investors make informed portfolio decisions through data-driven analysis, not hype.

## Tech Stack

- **Language:** Python 3.11+
- **Core:** pandas, numpy, scipy
- **Forecasting:** statsmodels, prophet (leverage DS background)
- **Data:** yfinance, FRED API (free macro data)
- **CLI:** typer or click
- **API (Phase 2):** FastAPI
- **Frontend (Phase 3):** Streamlit (fast for DS) or Next.js
- **Testing:** pytest
- **Docs:** mkdocs-material

## Architecture

```
finsight/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── src/
│   └── finsight/
│       ├── __init__.py
│       ├── cli.py                  # CLI entry point
│       ├── portfolio/
│       │   ├── __init__.py
│       │   ├── loader.py           # Load portfolio from CSV/JSON
│       │   ├── analyzer.py         # Risk metrics, diversification score
│       │   ├── rebalancer.py       # Suggest rebalancing moves
│       │   └── optimizer.py        # Mean-variance optimization
│       ├── market/
│       │   ├── __init__.py
│       │   ├── fetcher.py          # Pull prices via yfinance
│       │   ├── indicators.py       # Moving averages, RSI, volatility
│       │   └── macro.py            # FRED API — inflation, rates, GDP
│       ├── forecast/
│       │   ├── __init__.py
│       │   ├── returns.py          # Monte Carlo, historical projection
│       │   ├── trend.py            # Time series forecasting (Prophet/ARIMA)
│       │   └── scenario.py         # What-if scenario analysis
│       ├── advisor/
│       │   ├── __init__.py
│       │   ├── risk_profile.py     # Questionnaire & scoring
│       │   ├── recommendations.py  # Rule-based + LLM-powered insights
│       │   └── explainer.py        # Plain-language explanations
│       └── utils/
│           ├── __init__.py
│           ├── config.py
│           └── formatting.py
├── tests/
│   ├── test_portfolio/
│   ├── test_market/
│   ├── test_forecast/
│   └── test_advisor/
├── data/
│   └── sample_portfolio.csv
└── docs/
```

## Development Phases & GitHub Contribution Plan

### Phase 1 — Core Engine (Weeks 1–4)
Daily/weekly commits. Each feature = a PR with tests and docs.

- Week 1: Project scaffold, portfolio loader, basic CLI
- Week 2: Market data fetcher, portfolio analyzer (Sharpe ratio, volatility, max drawdown, diversification score)
- Week 3: Rebalancing engine, mean-variance optimizer
- Week 4: Monte Carlo simulation, historical return projections

### Phase 2 — Forecasting & Intelligence (Weeks 5–8)
This is where your DS background shines.

- Week 5: Time series forecasting with Prophet/ARIMA for price trends
- Week 6: Macro indicators integration (FRED API — CPI, Fed rate, yield curve)
- Week 7: Scenario analysis engine (what if rates rise 1%? what if recession?)
- Week 8: LLM-powered advisor layer — natural language Q&A about your portfolio

### Phase 3 — Product Layer (Weeks 9–12)
- Week 9: FastAPI backend
- Week 10: Streamlit dashboard with interactive charts
- Week 11: User auth, portfolio persistence
- Week 12: Deploy (Streamlit Community Cloud), write blog post, share on Reddit/HN

## Deployment & Distribution Plan

The primary public deployment is a **free, stateless demo on Streamlit
Community Cloud**, deployed straight from this GitHub repo:

- Users upload/paste a portfolio CSV or JSON for the session only — nothing
  is persisted server-side, no accounts, no database in the public demo.
- This avoids becoming a custodian of other people's financial data (see
  Privacy & Confidentiality) while still giving a free, clickable, public
  demo for the resume/portfolio goal.
- Users who want persistence, history, or to enter real personal data should
  **self-host** (clone the repo / run via Docker locally or on their own
  free-tier instance, e.g. Render, Railway, Hugging Face Spaces). Self-hosting
  is the supported path for any deployment that stores real user data.
- If auth + persistence are ever added to the hosted demo, they must use a
  managed provider (e.g. Supabase Auth + Supabase Postgres free tier) with
  per-user row-level security and encrypted sensitive columns — never a
  hand-rolled auth/DB layer holding plaintext financial data.

## Coding Standards

- Type hints on all functions
- Docstrings (NumPy style)
- pytest for every module — aim for 80%+ coverage
- Use Ruff for linting and formatting
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- Every feature on a branch, merged via PR (even solo — shows discipline)
- PRs use the template in `.github/PULL_REQUEST_TEMPLATE.md`. Pushing
  additional commits to an existing PR branch is fine and expected; **never
  merge to `main` without explicit confirmation from the repo owner.**
- README updated with each phase

## Key Differentiators (Resume Talking Points)

1. **Real forecasting models** — not just API wrappers. Prophet, ARIMA, Monte Carlo.
2. **Macro-aware** — integrates Fed rate, inflation, yield curve into recommendations.
3. **Scenario analysis** — "what if" engine that models portfolio impact of macro shifts.
4. **Clean software engineering** — typed, tested, documented, CI/CD.
5. **Built by someone who does this professionally** — financial KPI forecasting at Shell.

## Disclaimers

All output must include: "This is for educational and informational purposes only. Not financial advice. Consult a licensed financial advisor for personalized guidance."

## Privacy & Confidentiality

This agent handles sensitive personal financial data (holdings, balances, income, goals, risk tolerance).

- Never commit real portfolio data, account numbers, balances, or any personally identifiable information to the repo. Only `data/sample_portfolio.csv` (synthetic data) is tracked; `data/*.csv` and `data/*.json` are gitignored for this reason — keep it that way.
- Don't log raw user financial data to files, external services, or third-party APIs beyond what's strictly needed (e.g., ticker symbols to yfinance/FRED — never account values or personal identifiers).
- Any persistence layer (Phase 3 auth/storage) must store user data locally or encrypted, scoped per-user, and never shared across users.
- Sample/demo data, fixtures, and docs must use obviously fake figures, not real numbers from the maintainer's own portfolio.

## Daily Commit Ideas (When Stuck)

- Add a new risk metric
- Write a test for an edge case
- Improve a docstring
- Add a CLI flag
- Fix a type hint
- Add a sample portfolio
- Write a markdown doc explaining a concept
- Refactor a function for clarity
- Add input validation
- Update README with a usage example
