from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


TASK_SCOPE_TABLES = (
    "context_snapshots",
    "architectural_decisions",
    "command_history",
    "lessons_learned",
)
TASK_PLANNING_COLUMNS = (
    "parent_task_id",
    "task_kind",
    "sort_order",
    "depends_on",
    "acceptance_criteria",
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
    _ensure_task_planning_columns(engine, inspector, existing_tables, dialect)


def _ensure_task_planning_columns(engine: Engine, inspector, existing_tables: set[str], dialect: str) -> None:
    if "tasks" not in existing_tables:
        return
    column_names = {column["name"] for column in inspector.get_columns("tasks")}
    with engine.begin() as connection:
        if "parent_task_id" not in column_names:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN parent_task_id INTEGER NULL"))
        if "task_kind" not in column_names:
            task_kind_type = "VARCHAR(32)" if dialect == "mysql" else "TEXT"
            connection.execute(text(f"ALTER TABLE tasks ADD COLUMN task_kind {task_kind_type} NOT NULL DEFAULT 'task'"))
        if "sort_order" not in column_names:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"))
        if "depends_on" not in column_names:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN depends_on TEXT NULL"))
        if "acceptance_criteria" not in column_names:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN acceptance_criteria TEXT NULL"))


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
