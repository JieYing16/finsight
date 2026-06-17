"""FinSight CLI entry point."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from finsight.market.fetcher import enrich_portfolio
from finsight.portfolio.loader import load_portfolio
from finsight.portfolio.rebalancer import compute_rebalance, equal_weights

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


def _parse_target_weights(target: str) -> dict[str, float]:
    """Parse a 'TICKER=WEIGHT,...' string into a ticker -> weight dict."""
    weights: dict[str, float] = {}
    for pair in target.split(","):
        if "=" not in pair:
            raise ValueError(
                f"Invalid target weight pair: '{pair}'. Use TICKER=WEIGHT."
            )
        ticker, value = pair.split("=", 1)
        try:
            weights[ticker.strip().upper()] = float(value)
        except ValueError as exc:
            raise ValueError(f"Invalid weight value in '{pair}': {value}") from exc
    return weights


@app.command()
def rebalance(
    filepath: Path = typer.Argument(
        ..., help="Path to a .csv or .json portfolio file."
    ),
    target: str = typer.Option(
        None,
        help=(
            "Target weights as TICKER=WEIGHT pairs, comma-separated "
            "(e.g. 'VTI=0.4,BND=0.3,VEA=0.3'). Defaults to equal-weight "
            "across current holdings."
        ),
    ),
    threshold: float = typer.Option(
        1.0, help="Minimum drift in percentage points to suggest a trade."
    ),
) -> None:
    """Suggest rebalancing trades to reach target portfolio weights."""
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

    if target:
        try:
            target_weights = _parse_target_weights(target)
        except ValueError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc
    else:
        target_weights = equal_weights(raw["ticker"].tolist())

    try:
        trades = compute_rebalance(enriched, target_weights, threshold_pct=threshold)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Rebalancing — {filepath.name}", show_lines=True)
    table.add_column("Ticker", style="bold cyan")
    table.add_column("Current %", justify="right")
    table.add_column("Target %", justify="right")
    table.add_column("Drift", justify="right")
    table.add_column("Action", justify="center")
    table.add_column("Trade Value", justify="right")
    table.add_column("Shares", justify="right")

    action_color = {"buy": "green", "sell": "red", "hold": "dim"}
    for _, row in trades.iterrows():
        color = action_color[row["action"]]
        shares_str = "—" if pd.isna(row["shares"]) else f"{row['shares']:,.2f}"
        table.add_row(
            row["ticker"],
            f"{row['current_weight_pct']:.2f}%",
            f"{row['target_weight_pct']:.2f}%",
            f"{row['drift_pct']:+.2f}pp",
            f"[{color}]{row['action'].upper()}[/{color}]",
            f"${row['trade_value']:,.2f}",
            shares_str,
        )

    console.print(table)
    console.print(f"\n{_DISCLAIMER}")


if __name__ == "__main__":
    app()
