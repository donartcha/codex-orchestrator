from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


TASK_SCOPE_TABLES = (
    "context_snapshots",
    "architectural_decisions",
    "command_history",
    "lessons_learned",
)
INITIAL_LESSON_CATEGORIES = (
    ("powershell", "PowerShell", "Errores de sintaxis, quoting, rutas y comandos en PowerShell."),
    ("python-environment", "Python Environment", "Intérpretes, venv, imports, dependencias y resolución de Python."),
    ("memory-backend", "Memory Backend", "MariaDB, SQLite, file fallback y degradaciones de backend."),
    ("validation", "Validation", "Tests, checks, hooks, compilación y validaciones de entrega."),
    ("testing", "Testing", "Compat category for existing lessons/tests."),
    ("database", "Database", "Esquemas, migraciones, SQL y restricciones."),
    ("git-workflow", "Git Workflow", "Ramas, commits, merges, releases y publicación."),
    ("npm-publishing", "NPM Publishing", "Publicación de paquetes, versionado y errores de npm."),
    ("openlag-cli", "OpenLAG CLI", "Comandos y contratos del CLI de OpenLAG."),
    ("documentation", "Documentation", "README, API y consistencia documental."),
    ("agent-policy", "Agent Policy", "Reglas operativas de agentes, memoria y orquestación."),
    ("security", "Security", "Secretos, sanitización y exposición de datos."),
    ("shell-compatibility", "Shell Compatibility", "Diferencias Bash/PowerShell/cmd/WSL."),
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
    _ensure_lesson_category_catalog(engine, inspector, existing_tables, dialect)


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


def _ensure_lesson_category_catalog(engine: Engine, inspector, existing_tables: set[str], dialect: str) -> None:
    with engine.begin() as connection:
        if "lesson_categories" not in existing_tables:
            connection.execute(
                text(
                    "CREATE TABLE lesson_categories ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "key_name TEXT NOT NULL UNIQUE, "
                    "title TEXT NOT NULL, "
                    "description TEXT NULL, "
                    "parent_id INTEGER NULL, "
                    "status TEXT NOT NULL DEFAULT 'active', "
                    "created_at TEXT DEFAULT CURRENT_TIMESTAMP, "
                    "updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
                )
            )
            existing_tables.add("lesson_categories")
        if "lessons_learned" in existing_tables:
            lesson_columns = {column["name"] for column in inspector.get_columns("lessons_learned")}
            if "category_id" not in lesson_columns:
                connection.execute(text("ALTER TABLE lessons_learned ADD COLUMN category_id INTEGER NULL"))
        for key_name, title, description in INITIAL_LESSON_CATEGORIES:
            connection.execute(
                text(
                    "INSERT INTO lesson_categories (key_name, title, description, status) "
                    "SELECT :key_name, :title, :description, 'active' "
                    "WHERE NOT EXISTS (SELECT 1 FROM lesson_categories WHERE key_name = :key_name)"
                ),
                {"key_name": key_name, "title": title, "description": description},
            )


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
