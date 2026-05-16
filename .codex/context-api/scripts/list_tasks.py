from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def main(
    status: str = typer.Option("pending", "--status", "-s", help="Task status to list."),
) -> None:
    try:
        with open_context() as context:
            tasks = context.tasks(status=status)

        table = Table(title=f"Tasks with status: {status}")
        table.add_column("ID", justify="right")
        table.add_column("Priority")
        table.add_column("Agent")
        table.add_column("Title")
        table.add_column("Created")

        for task in tasks:
            table.add_row(
                str(task.id),
                task.priority,
                task.assigned_agent or "",
                task.title,
                str(task.created_at),
            )

        console.print(table)
        console.print(f"{len(tasks)} task(s) found.")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
