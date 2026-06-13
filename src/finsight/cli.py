"""FinSight CLI entry point."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

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
    filepath: Path = typer.Argument(..., help="Path to a .csv or .json portfolio file."),
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
    console.print(f"\n[bold]Total portfolio value (at cost):[/bold] ${total_value:,.2f}")
    console.print(f"[bold]Holdings:[/bold] {len(df)}")
    console.print(f"\n{_DISCLAIMER}")


if __name__ == "__main__":
    app()
