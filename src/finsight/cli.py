"""FinSight CLI entry point."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from finsight.market.fetcher import enrich_portfolio, fetch_historical_prices
from finsight.portfolio.analyzer import analyze_portfolio
from finsight.portfolio.loader import load_portfolio

app = typer.Typer(
    name="finsight",
    help="FinSight — data-driven personal financial advisor.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


@app.callback()
def _callback() -> None:
    """FinSight — data-driven personal financial advisor."""

_DISCLAIMER = (
    "[dim]This is for educational and informational purposes only. "
    "Not financial advice. Consult a licensed financial advisor for "
    "personalized guidance.[/dim]"
)


@app.command()
def load(
    filepath: Path = typer.Argument(
        ..., help="Path to a .csv or .json portfolio file."
    ),
) -> None:
    """Load a portfolio file and display a summary table."""
    try:
        df = load_portfolio(filepath)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    df["market_value"] = df["shares"] * df["purchase_price"]
    total_value = df["market_value"].sum()
    df["weight_%"] = (df["market_value"] / total_value * 100).round(2)

    table = Table(title=f"Portfolio — {filepath.name}", show_lines=True)
    table.add_column("Ticker", style="bold cyan")
    table.add_column("Shares", justify="right")
    table.add_column("Purchase Price", justify="right")
    table.add_column("Purchase Date")
    table.add_column("Market Value", justify="right", style="green")
    table.add_column("Weight %", justify="right")

    for _, row in df.iterrows():
        table.add_row(
            row["ticker"],
            f"{row['shares']:,.2f}",
            f"${row['purchase_price']:,.2f}",
            str(row["purchase_date"].date()),
            f"${row['market_value']:,.2f}",
            f"{row['weight_%']}%",
        )

    console.print(table)
    console.print(
        f"\n[bold]Total portfolio value (at cost):[/bold] ${total_value:,.2f}"
    )
    console.print(f"[bold]Holdings:[/bold] {len(df)}")
    console.print(f"\n{_DISCLAIMER}")


@app.command()
def summary(
    filepath: Path = typer.Argument(
        ..., help="Path to a .csv or .json portfolio file."
    ),
) -> None:
    """Load a portfolio and display live market prices with P&L."""
    try:
        raw = load_portfolio(filepath)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print("[dim]Fetching live prices…[/dim]")
    try:
        df = enrich_portfolio(raw)
    except ValueError as exc:
        console.print(f"[red]Error fetching prices:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Portfolio Summary — {filepath.name}", show_lines=True)
    table.add_column("Ticker", style="bold cyan")
    table.add_column("Shares", justify="right")
    table.add_column("Cost Basis", justify="right")
    table.add_column("Current Price", justify="right")
    table.add_column("Market Value", justify="right", style="green")
    table.add_column("Gain / Loss", justify="right")
    table.add_column("G/L %", justify="right")
    table.add_column("Weight %", justify="right")

    for _, row in df.iterrows():
        gl = row["gain_loss"]
        glp = row["gain_loss_pct"]
        gl_str = (
            f"[green]+${gl:,.2f}[/green]" if gl >= 0 else f"[red]-${abs(gl):,.2f}[/red]"
        )
        glp_str = (
            f"[green]+{glp:.2f}%[/green]" if glp >= 0 else f"[red]{glp:.2f}%[/red]"
        )
        table.add_row(
            row["ticker"],
            f"{row['shares']:,.2f}",
            f"${row['cost_basis']:,.2f}",
            f"${row['current_price']:,.2f}",
            f"${row['market_value']:,.2f}",
            gl_str,
            glp_str,
            f"{row['weight_pct']}%",
        )

    console.print(table)

    total_value = df["market_value"].sum()
    total_cost = df["cost_basis"].sum()
    total_gl = total_value - total_cost
    sign = "+" if total_gl >= 0 else ""
    gl_summary = f"{sign}${total_gl:,.2f} ({sign}{total_gl / total_cost * 100:.2f}%)"
    console.print(f"\n[bold]Total market value:[/bold] ${total_value:,.2f}")
    console.print(f"[bold]Total cost basis:[/bold]   ${total_cost:,.2f}")
    console.print(f"[bold]Total gain / loss:[/bold]  {gl_summary}")
    console.print(f"\n{_DISCLAIMER}")


def _period_to_start(period: str, today: date) -> date:
    """Convert a period string like '1y', '6mo', '3mo' to a start date."""
    period = period.lower().strip()
    if period.endswith("y"):
        years = int(period[:-1])
        return date(today.year - years, today.month, today.day)
    if period.endswith("mo"):
        months = int(period[:-2])
        year = today.year + (today.month - months - 1) // 12
        month = (today.month - months - 1) % 12 + 1
        return date(year, month, today.day)
    if period.endswith("d"):
        days = int(period[:-1])
        return today - timedelta(days=days)
    raise ValueError(f"Unrecognised period '{period}'. Use e.g. 1y, 6mo, 90d.")


@app.command()
def analyze(
    filepath: Path = typer.Argument(
        ..., help="Path to a .csv or .json portfolio file."
    ),
    period: str = typer.Option(
        "1y", help="Historical window for risk metrics (e.g. 1y, 6mo, 90d)."
    ),
    risk_free_rate: float = typer.Option(
        0.05, help="Annual risk-free rate for Sharpe ratio (default 0.05 = 5%)."
    ),
) -> None:
    """Analyze portfolio risk: Sharpe ratio, volatility, max drawdown, diversification."""
    try:
        raw = load_portfolio(filepath)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print("[dim]Fetching live prices…[/dim]")
    try:
        enriched = enrich_portfolio(raw)
    except ValueError as exc:
        console.print(f"[red]Error fetching prices:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print("[dim]Fetching historical prices…[/dim]")
    try:
        start = _period_to_start(period, date.today())
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    tickers = raw["ticker"].tolist()
    try:
        hist = fetch_historical_prices(tickers, start=start, end=date.today())
    except ValueError as exc:
        console.print(f"[red]Error fetching historical data:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    metrics = analyze_portfolio(enriched, hist, risk_free_rate=risk_free_rate)

    table = Table(title=f"Risk Analysis — {filepath.name} ({period})", show_lines=True)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    def _pct(v: float, decimals: int = 2) -> str:
        return f"{v * 100:.{decimals}f}%"

    sharpe = metrics["sharpe"]
    sharpe_color = "green" if sharpe >= 1.0 else "yellow" if sharpe >= 0.5 else "red"
    hhi = metrics["herfindahl"]
    n = int(metrics["n_holdings"])

    table.add_row("Holdings", str(n))
    table.add_row("Top holding weight", f"{metrics['top_holding_weight']:.1f}%")
    table.add_row("Annualized volatility", _pct(metrics["volatility"]))
    table.add_row("Max drawdown", _pct(metrics["max_drawdown"]))
    table.add_row(
        "Sharpe ratio",
        f"[{sharpe_color}]{sharpe:.2f}[/{sharpe_color}]",
    )
    table.add_row(
        "Herfindahl index (HHI)",
        f"{hhi:.4f}  [dim](1/{n} = {1/n:.4f} perfectly diversified)[/dim]",
    )

    console.print(table)
    console.print(
        f"\n[dim]Risk-free rate used: {risk_free_rate * 100:.1f}% · "
        f"Historical window: {period}[/dim]"
    )
    console.print(f"\n{_DISCLAIMER}")


if __name__ == "__main__":
    app()
