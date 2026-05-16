from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def main(
    category: str = typer.Option("", "--category", "-c", help="Optional lesson category filter."),
) -> None:
    try:
        with open_context() as context:
            lessons = context.lessons(category or None)

        table = Table(title="Lessons learned")
        table.add_column("ID", justify="right")
        table.add_column("Category")
        table.add_column("Problem")
        table.add_column("Created")

        for lesson in lessons:
            table.add_row(
                str(lesson.id),
                lesson.category or "",
                lesson.problem_description or "",
                str(lesson.created_at),
            )

        console.print(table)
        console.print(f"{len(lessons)} lesson(s) found.")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
