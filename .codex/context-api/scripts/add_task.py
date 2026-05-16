from __future__ import annotations

import typer
from rich.console import Console

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def main(
    title: str = typer.Argument(..., help="Task title."),
    description: str = typer.Argument(..., help="Task description."),
    assigned_agent: str = typer.Option("", "--assigned-agent", "-a", help="Agent assigned to the task."),
    priority: str = typer.Option("normal", "--priority", "-p", help="Task priority."),
) -> None:
    try:
        with open_context() as context:
            task = context.remember_task(
                title=title,
                description=description,
                assigned_agent=assigned_agent or None,
                priority=priority,
            )
            console.print(f"[green]Task added[/green] id={task.id} title={task.title!r}")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
