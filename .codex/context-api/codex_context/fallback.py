from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

from .backends import BackendStatus, ContextBackend, FileBackend, MariaDBBackend, SQLiteBackend


@dataclass(frozen=True)
class BackendSelection:
    backend: ContextBackend
    attempts: list[BackendStatus] = field(default_factory=list)

    @property
    def status(self) -> BackendStatus:
        return self.backend.status


def select_backend() -> BackendSelection:
    attempts: list[BackendStatus] = []

    if os.environ.get("CODEX_CONTEXT_DISABLE_MARIADB") == "1":
        mariadb_error = "MariaDB disabled by CODEX_CONTEXT_DISABLE_MARIADB."
    else:
        try:
            backend = MariaDBBackend()
            attempts.append(backend.status)
            return BackendSelection(backend=backend, attempts=attempts)
        except Exception as exc:
            mariadb_error = f"{type(exc).__name__}: {exc}"
    attempts.append(BackendStatus(name="mariadb", active=False, warning=mariadb_error))

    sqlite_warning = "MariaDB unavailable. Using SQLite fallback."
    if os.environ.get("CODEX_CONTEXT_DISABLE_SQLITE") == "1":
        sqlite_error = "SQLite disabled by CODEX_CONTEXT_DISABLE_SQLITE."
    else:
        try:
            backend = SQLiteBackend(warning=sqlite_warning)
            attempts.append(backend.status)
            _warn_once(sqlite_warning)
            return BackendSelection(backend=backend, attempts=attempts)
        except Exception as exc:
            sqlite_error = f"{type(exc).__name__}: {exc}"
    attempts.append(BackendStatus(name="sqlite", active=False, warning=sqlite_error))

    file_warning = "MariaDB and SQLite unavailable. Using JSON/Markdown file fallback."
    backend = FileBackend(warning=file_warning)
    attempts.append(backend.status)
    _warn_once(file_warning)
    return BackendSelection(backend=backend, attempts=attempts)


def _warn_once(message: str) -> None:
    if os.environ.get("CODEX_CONTEXT_SUPPRESS_FALLBACK_WARNING") == "1":
        return
    print(f"WARNING: {message}", file=sys.stderr)
