from __future__ import annotations

import typer
from rich.console import Console

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def main() -> None:
    try:
        with open_context() as context:
            context.tasks(status="pending", limit=1)
        console.print("[green]Connection OK[/green]")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print("[red]Database connection failed.[/red]")
        console.print("Check CODEX_DB_HOST, CODEX_DB_PORT, CODEX_DB_NAME, CODEX_DB_USER and CODEX_DB_PASSWORD in .env.")
        console.print(f"Message: {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
