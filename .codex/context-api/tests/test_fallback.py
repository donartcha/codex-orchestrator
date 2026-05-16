from __future__ import annotations

import pytest

from codex_context.fallback import select_backend


@pytest.mark.fallback
def test_select_backend_uses_sqlite_when_mariadb_disabled(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CODEX_CONTEXT_DISABLE_MARIADB", "1")
    monkeypatch.setenv("CODEX_CONTEXT_SQLITE_PATH", str(tmp_path / "memory.sqlite3"))
    monkeypatch.setenv("CODEX_CONTEXT_SUPPRESS_FALLBACK_WARNING", "1")

    selection = select_backend()
    try:
        assert selection.status.name == "sqlite"
        assert selection.status.degraded is True
        assert [attempt.name for attempt in selection.attempts] == ["mariadb", "sqlite"]
    finally:
        selection.backend.close()


@pytest.mark.fallback
def test_select_backend_uses_file_when_mariadb_and_sqlite_disabled(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CODEX_CONTEXT_DISABLE_MARIADB", "1")
    monkeypatch.setenv("CODEX_CONTEXT_DISABLE_SQLITE", "1")
    monkeypatch.setenv("CODEX_CONTEXT_FILE_PATH", str(tmp_path / "memory.json"))
    monkeypatch.setenv("CODEX_CONTEXT_SUPPRESS_FALLBACK_WARNING", "1")

    selection = select_backend()
    try:
        assert selection.status.name == "file"
        assert selection.status.degraded is True
        assert [attempt.name for attempt in selection.attempts] == ["mariadb", "sqlite", "file"]
    finally:
        selection.backend.close()
