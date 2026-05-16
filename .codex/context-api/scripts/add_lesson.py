from __future__ import annotations

import typer
from rich.console import Console

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def main(
    category: str = typer.Argument(..., help="Lesson category."),
    problem_description: str = typer.Argument(..., help="Problem description."),
    solution_description: str = typer.Argument(..., help="Solution description."),
    prevention_strategy: str = typer.Argument(..., help="How to prevent recurrence."),
) -> None:
    try:
        with open_context() as context:
            lesson = context.remember_lesson(
                category=category,
                problem_description=problem_description,
                solution_description=solution_description,
                prevention_strategy=prevention_strategy,
            )
            console.print(f"[green]Lesson added[/green] id={lesson.id} category={lesson.category!r}")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
