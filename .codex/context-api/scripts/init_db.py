from __future__ import annotations

import typer
from rich.console import Console
from sqlalchemy.exc import OperationalError, SQLAlchemyError

import _bootstrap  # noqa: F401
from codex_context.config import ConfigError, load_config
from codex_context.db import create_db_engine
from codex_context.models import Base
from codex_context.schema_migrations import ensure_task_scope_columns


console = Console()


def main() -> None:
    engine = None
    try:
        config = load_config()
        engine = create_db_engine(config)
        Base.metadata.create_all(engine)
        ensure_task_scope_columns(engine)
        console.print(f"[green]Tables are ready[/green] ({config.safe_label})")
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except OperationalError as exc:
        console.print("[red]Database connection failed while creating tables.[/red]")
        console.print("No destructive migrations were run.")
        console.print("Check the database exists and .env values are correct.")
        console.print(f"Driver message: {exc.orig}")
        raise typer.Exit(1) from exc
    except SQLAlchemyError as exc:
        console.print(f"[red]SQLAlchemy error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    typer.run(main)
