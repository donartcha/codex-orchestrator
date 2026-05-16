from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError
from codex_context.context import open_context


console = Console()


def main(
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of command rows."),
) -> None:
    try:
        with open_context() as context:
            commands = context.commands(limit)

        table = Table(title="Command history")
        table.add_column("ID", justify="right")
        table.add_column("Agent")
        table.add_column("Shell")
        table.add_column("OK")
        table.add_column("Command")
        table.add_column("Created")

        for command in commands:
            table.add_row(
                str(command.id),
                command.agent_name or "",
                command.shell_type or "",
                str(bool(command.success_flag)),
                command.command_text,
                str(command.created_at),
            )

        console.print(table)
        console.print(f"{len(commands)} command(s) found.")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Memory error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    typer.run(main)
