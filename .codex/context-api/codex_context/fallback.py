from __future__ import annotations

import os
import sys
import time
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
        backend, mariadb_error = _connect_mariadb_with_retry()
        if backend is not None:
            attempts.append(backend.status)
            return BackendSelection(backend=backend, attempts=attempts)
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


def _connect_mariadb_with_retry(max_attempts: int = 3, delay_seconds: float = 0.25) -> tuple[ContextBackend | None, str]:
    last_error = "Unknown MariaDB error."
    for attempt in range(1, max_attempts + 1):
        try:
            return MariaDBBackend(), ""
        except Exception as exc:  # noqa: BLE001
            message = f"{type(exc).__name__}: {exc}"
            last_error = message
            if not _is_transient_mariadb_error(message):
                return None, message
            if attempt < max_attempts:
                time.sleep(delay_seconds)
    return None, last_error


def _is_transient_mariadb_error(message: str) -> bool:
    lowered = message.lower()
    transient_markers = (
        "deadlock found when trying to get lock",
        "(1213",
        "lock wait timeout exceeded",
        "(1205",
        "lost connection to mysql server",
        "(2013",
        "server has gone away",
        "(2006",
    )
    return any(marker in lowered for marker in transient_markers)
