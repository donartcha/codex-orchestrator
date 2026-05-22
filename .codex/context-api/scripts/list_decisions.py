from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def main(
    status: str = typer.Option("", "--status", "-s", help="Optional decision status filter."),
    task_id: int | None = typer.Option(None, "--task-id", "-t", help="Optional related task id."),
) -> None:
    try:
        with open_context() as context:
            decisions = context.decisions(status or None, task_id=task_id)

        table = Table(title="Architectural decisions")
        table.add_column("ID", justify="right")
        table.add_column("Task")
        table.add_column("Key")
        table.add_column("Status")
        table.add_column("Title")
        table.add_column("Created")

        for decision in decisions:
            table.add_row(
                str(decision.id),
                str(decision.task_id or ""),
                decision.decision_key,
                decision.status or "",
                decision.title,
                str(decision.created_at),
            )

        console.print(table)
        console.print(f"{len(decisions)} decision(s) found.")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
