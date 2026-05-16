#!/usr/bin/env python
"""Reject local-only files that should never be committed."""

from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath


SQLITE_SUFFIXES = {".sqlite", ".sqlite3", ".sqlite-shm", ".sqlite-wal"}


def normalized_parts(filename: str) -> tuple[str, ...]:
    return PurePosixPath(filename.replace("\\", "/")).parts


def is_env_file(parts: tuple[str, ...]) -> bool:
    name = parts[-1] if parts else ""
    if name == ".env.example":
        return False
    return name == ".env" or name.startswith(".env.")


def has_venv_part(parts: tuple[str, ...]) -> bool:
    return any(part in {".venv", "venv"} for part in parts)


def has_sqlite_suffix(path: Path) -> bool:
    lower_name = path.name.lower()
    return path.suffix.lower() in SQLITE_SUFFIXES or any(
        lower_name.endswith(suffix) for suffix in SQLITE_SUFFIXES
    )


def has_sqlite_header(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(16) == b"SQLite format 3\0"
    except OSError:
        return False


def check_file(filename: str) -> list[str]:
    path = Path(filename)
    parts = normalized_parts(filename)
    failures: list[str] = []

    if is_env_file(parts):
        failures.append(f"{filename}: .env files may contain secrets; commit .env.example instead")

    if has_venv_part(parts):
        failures.append(f"{filename}: virtual environments must stay local")

    if has_sqlite_suffix(path) or (path.is_file() and has_sqlite_header(path)):
        failures.append(f"{filename}: SQLite database files must stay local")

    return failures


def main(argv: list[str]) -> int:
    failures: list[str] = []
    for filename in argv:
        failures.extend(check_file(filename))

    if failures:
        print("Forbidden local files detected:")
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
