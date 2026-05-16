from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def _remember_summary(summary: str, task_id: int | None, next_steps: str) -> None:
    if task_id is None:
        console.print("[red]--summary requires --task-id so the summary can be stored as a task log.[/red]")
        raise typer.Exit(1)
    content = summary if not next_steps else f"{summary}\n\nNext steps: {next_steps}"
    with open_context() as context:
        task_log = context.remember_task_log(
            task_id=task_id,
            content=content,
            agent_name="codex",
            log_type="summary",
        )
    console.print(f"[green]Summary recorded[/green] task_log_id={task_log.id} task_id={task_log.task_id}")


def _update_task_status(task_id: int, status: str) -> None:
    with open_context() as context:
        task = context.set_task_status(task_id, status)
    if task is None:
        console.print(f"[red]Task not found:[/red] {task_id}")
        raise typer.Exit(1)
    console.print(f"[green]Task updated[/green] id={task.id} status={task.status}")


def _remember_lesson(category: str, problem: str, solution: str, prevention: str) -> None:
    with open_context() as context:
        lesson = context.remember_lesson(
            category=category,
            problem_description=problem,
            solution_description=solution,
            prevention_strategy=prevention,
        )
    console.print(f"[green]Lesson recorded[/green] id={lesson.id} category={lesson.category!r}")


def _remember_follow_up(title: str, description: str, assigned_agent: str, priority: str) -> None:
    with open_context() as context:
        task = context.remember_task(
            title=title,
            description=description,
            assigned_agent=assigned_agent or None,
            priority=priority,
        )
    console.print(f"[green]Follow-up task recorded[/green] id={task.id} title={task.title!r}")


def main(
    task_id: int | None = typer.Option(None, "--task-id", "-t", help="Task id to update or summarize."),
    status: str = typer.Option("", "--status", "-s", help="New status for --task-id."),
    summary: str = typer.Option("", "--summary", help="Task completion summary to persist as a task log."),
    next_steps: str = typer.Option("", "--next-steps", help="Next steps or prevention notes for the summary."),
    lesson_category: str = typer.Option("", "--lesson-category", help="Category for a reusable lesson."),
    lesson_problem: str = typer.Option("", "--lesson-problem", help="Problem description for a reusable lesson."),
    lesson_solution: str = typer.Option("", "--lesson-solution", help="Solution description for a reusable lesson."),
    lesson_prevention: str = typer.Option("", "--lesson-prevention", help="Prevention strategy for a reusable lesson."),
    follow_up_title: str = typer.Option("", "--follow-up-title", help="Title for one follow-up task."),
    follow_up_description: str = typer.Option("", "--follow-up-description", help="Description for one follow-up task."),
    follow_up_agent: str = typer.Option("", "--follow-up-agent", help="Agent assigned to the follow-up task."),
    follow_up_priority: str = typer.Option("normal", "--follow-up-priority", help="Priority for the follow-up task."),
) -> None:
    """Record the memory updates Codex should write after work."""
    try:
        console.print(Panel.fit("Codex memory finish", style="bold cyan"))

        if status and task_id is None:
            console.print("[red]--status requires --task-id.[/red]")
            raise typer.Exit(1)

        if task_id is not None and status:
            _update_task_status(task_id, status)

        if summary:
            _remember_summary(summary, task_id, next_steps)

        lesson_fields = [lesson_category, lesson_problem, lesson_solution, lesson_prevention]
        if any(lesson_fields):
            if not all(lesson_fields):
                console.print("[red]Lesson recording requires --lesson-category, --lesson-problem, --lesson-solution and --lesson-prevention.[/red]")
                raise typer.Exit(1)
            _remember_lesson(lesson_category, lesson_problem, lesson_solution, lesson_prevention)

        follow_up_fields = [follow_up_title, follow_up_description]
        if any(follow_up_fields):
            if not all(follow_up_fields):
                console.print("[red]Follow-up recording requires --follow-up-title and --follow-up-description.[/red]")
                raise typer.Exit(1)
            _remember_follow_up(follow_up_title, follow_up_description, follow_up_agent, follow_up_priority)

        if not any([status, summary, *lesson_fields, *follow_up_fields]):
            console.print("[yellow]No updates requested.[/yellow]")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
