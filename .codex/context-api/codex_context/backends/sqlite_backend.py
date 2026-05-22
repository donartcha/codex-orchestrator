from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ..models import Base
from ..schema_migrations import ensure_task_scope_columns
from .base import BackendStatus
from .mariadb_backend import MariaDBBackend

CONTEXT_API_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = CONTEXT_API_ROOT / "context-fallback.sqlite3"


class SQLiteBackend(MariaDBBackend):
    name = "sqlite"

    def __init__(self, path: str | Path | None = None, engine: Engine | None = None, warning: str | None = None) -> None:
        self._owns_engine = engine is None
        sqlite_path = Path(path or os.environ.get("CODEX_CONTEXT_SQLITE_PATH") or DEFAULT_SQLITE_PATH)
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = engine or create_engine(f"sqlite:///{sqlite_path}", future=True)
        with self.engine.begin() as connection:
            connection.execute(text("SELECT 1"))
            Base.metadata.create_all(connection)
        ensure_task_scope_columns(self.engine)
        self.path = sqlite_path
        self.status = BackendStatus(
            name=self.name,
            active=True,
            degraded=True,
            warning=warning,
            details={"path": str(sqlite_path)},
        )
