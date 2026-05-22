from __future__ import annotations

import typer
from rich.console import Console

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def main(
    agent_name: str = typer.Argument(..., help="Agent name."),
    shell_type: str = typer.Argument(..., help="Shell type, for example powershell."),
    command_text: str = typer.Argument(..., help="Command that was executed."),
    success_flag: bool = typer.Option(False, "--success-flag/--failed", help="Whether the command succeeded."),
    error_message: str = typer.Option("", "--error-message", help="Error message, if any."),
    correction_applied: str = typer.Option("", "--correction-applied", help="Correction that fixed or mitigated the issue."),
    task_id: int | None = typer.Option(None, "--task-id", "-t", help="Optional related task id."),
) -> None:
    try:
        with open_context() as context:
            command = context.remember_command(
                agent_name=agent_name,
                shell_type=shell_type,
                command_text=command_text,
                success_flag=success_flag,
                error_message=error_message or None,
                correction_applied=correction_applied or None,
                task_id=task_id,
            )
            console.print(f"[green]Command log added[/green] id={command.id} success={command.success_flag}")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
