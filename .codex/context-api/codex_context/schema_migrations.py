from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


TASK_SCOPE_TABLES = (
    "context_snapshots",
    "architectural_decisions",
    "command_history",
    "lessons_learned",
)


def ensure_task_scope_columns(engine: Engine) -> None:
    """Apply idempotent lightweight schema updates not covered by create_all()."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    dialect = engine.dialect.name
    for table_name in TASK_SCOPE_TABLES:
        if table_name not in existing_tables:
            continue
        column_names = {column["name"] for column in inspector.get_columns(table_name)}
        if "task_id" in column_names:
            continue
        if dialect == "mysql":
            _add_mysql_task_id(engine, table_name)
        elif dialect == "sqlite":
            _add_sqlite_task_id(engine, table_name)


def _add_mysql_task_id(engine: Engine, table_name: str) -> None:
    index_name = f"idx_{table_name}_task_id"
    constraint_name = f"fk_{table_name}_task_id"
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE `{table_name}` ADD COLUMN task_id BIGINT NULL"))
        connection.execute(text(f"CREATE INDEX `{index_name}` ON `{table_name}` (task_id)"))
        connection.execute(
            text(
                f"ALTER TABLE `{table_name}` "
                f"ADD CONSTRAINT `{constraint_name}` "
                "FOREIGN KEY (task_id) REFERENCES `tasks` (`id`) ON DELETE SET NULL"
            )
        )


def _add_sqlite_task_id(engine: Engine, table_name: str) -> None:
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL"))
        connection.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_task_id ON {table_name} (task_id)"))
