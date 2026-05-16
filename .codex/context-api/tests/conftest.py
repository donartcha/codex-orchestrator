from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from codex_context.backends import FileBackend, SQLiteBackend


CONTEXT_API_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def context_api_root() -> Path:
    return CONTEXT_API_ROOT


@pytest.fixture
def cli_command(context_api_root: Path) -> list[str]:
    return [sys.executable, str(context_api_root / "codex_memory.py")]


@pytest.fixture
def isolated_context_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["CODEX_CONTEXT_DISABLE_MARIADB"] = "1"
    env["CODEX_CONTEXT_SUPPRESS_FALLBACK_WARNING"] = "1"
    env["CODEX_CONTEXT_FILE_PATH"] = str(tmp_path / "memory-fallback.json")
    env["CODEX_CONTEXT_SQLITE_PATH"] = str(tmp_path / "context-fallback.sqlite3")
    return env


@pytest.fixture
def file_backend(tmp_path: Path) -> Iterator[FileBackend]:
    backend = FileBackend(path=tmp_path / "memory.json")
    try:
        yield backend
    finally:
        backend.close()


@pytest.fixture
def sqlite_backend(tmp_path: Path) -> Iterator[SQLiteBackend]:
    backend = SQLiteBackend(path=tmp_path / "memory.sqlite3")
    try:
        yield backend
    finally:
        backend.close()
