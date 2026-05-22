from __future__ import annotations

import typer
from rich.console import Console

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def main(
    decision_key: str = typer.Argument(..., help="Stable unique decision key."),
    title: str = typer.Argument(..., help="Decision title."),
    rationale: str = typer.Argument(..., help="Why this decision was taken."),
    consequences: str = typer.Argument(..., help="Expected consequences."),
    task_id: int | None = typer.Option(None, "--task-id", "-t", help="Optional related task id."),
) -> None:
    try:
        with open_context() as context:
            decision = context.remember_decision(decision_key, title, rationale, consequences, task_id=task_id)
            console.print(f"[green]Decision added[/green] id={decision.id} key={decision.decision_key!r}")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
