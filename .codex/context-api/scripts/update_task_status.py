from __future__ import annotations

import typer
from rich.console import Console

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def main(
    task_id: int = typer.Argument(..., help="Task id."),
    status: str = typer.Argument(..., help="New task status."),
) -> None:
    try:
        with open_context() as context:
            task = context.set_task_status(task_id, status)
        if task is None:
            console.print(f"[red]Task not found:[/red] {task_id}")
            raise typer.Exit(1)
        console.print(f"[green]Task updated[/green] id={task.id} status={task.status}")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
