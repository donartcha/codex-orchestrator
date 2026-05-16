from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def _clip(value: object, limit: int = 120) -> str:
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _print_tasks(status: str, limit: int) -> None:
    with open_context() as context:
        tasks = context.tasks(status, limit=limit)

    table = Table(title=f"Pending tasks ({status})")
    table.add_column("ID", justify="right")
    table.add_column("Priority")
    table.add_column("Agent")
    table.add_column("Title")
    table.add_column("Created")

    for task in tasks:
        table.add_row(
            str(task.id),
            task.priority or "",
            task.assigned_agent or "",
            _clip(task.title, 80),
            str(task.created_at),
        )

    console.print(table)
    console.print(f"{len(tasks)} task(s) shown.")


def _print_decisions(limit: int) -> None:
    with open_context() as context:
        decisions = context.decisions(limit=limit)

    table = Table(title="Recent decisions")
    table.add_column("ID", justify="right")
    table.add_column("Key")
    table.add_column("Status")
    table.add_column("Title")
    table.add_column("Created")

    for decision in decisions:
        table.add_row(
            str(decision.id),
            _clip(decision.decision_key, 40),
            decision.status or "",
            _clip(decision.title, 80),
            str(decision.created_at),
        )

    console.print(table)
    console.print(f"{len(decisions)} decision(s) shown.")


def _print_lessons(limit: int, category: str | None) -> None:
    with open_context() as context:
        lessons = context.lessons(category, limit=limit)

    title = "Recent lessons" if category is None else f"Recent lessons ({category})"
    table = Table(title=title)
    table.add_column("ID", justify="right")
    table.add_column("Category")
    table.add_column("Problem")
    table.add_column("Created")

    for lesson in lessons:
        table.add_row(
            str(lesson.id),
            lesson.category or "",
            _clip(lesson.problem_description, 100),
            str(lesson.created_at),
        )

    console.print(table)
    console.print(f"{len(lessons)} lesson(s) shown.")


def _print_failed_commands(limit: int) -> None:
    with open_context() as context:
        failed_commands = context.commands(limit, success_flag=False)

    table = Table(title="Recent failed commands")
    table.add_column("ID", justify="right")
    table.add_column("Agent")
    table.add_column("Shell")
    table.add_column("Command")
    table.add_column("Error")
    table.add_column("Created")

    for command in failed_commands:
        table.add_row(
            str(command.id),
            command.agent_name or "",
            command.shell_type or "",
            _clip(command.command_text, 80),
            _clip(command.error_message, 80),
            str(command.created_at),
        )

    console.print(table)
    console.print(f"{len(failed_commands)} failed command(s) shown.")


def main(
    status: str = typer.Option("pending", "--status", "-s", help="Task status to show."),
    limit: int = typer.Option(5, "--limit", "-n", min=1, help="Rows to show per section."),
    lesson_category: str = typer.Option("", "--lesson-category", "-c", help="Optional lesson category filter."),
    include_commands: bool = typer.Option(True, "--commands/--no-commands", help="Show recent failed commands."),
) -> None:
    """Show the relevant memory bundle Codex should read before work."""
    try:
        console.print(Panel.fit("Codex memory bootstrap", style="bold cyan"))
        _print_tasks(status, limit)
        _print_decisions(limit)
        _print_lessons(limit, lesson_category or None)
        if include_commands:
            _print_failed_commands(limit)
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
