#!/usr/bin/env python
"""Reject machine-local absolute paths in text files."""

from __future__ import annotations

import re
import sys
from pathlib import Path


WINDOWS_DEV = r"D:" + re.escape("\\") + r"dev" + re.escape("\\")
WINDOWS_USERS = r"C:" + re.escape("\\") + r"Users" + re.escape("\\")
POSIX_HOME = "/" + "home" + "/"
MAC_USERS = "/" + "Users" + "/"

RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("Windows workspace absolute path", re.compile(WINDOWS_DEV, re.IGNORECASE), ".codex/ or another repository-relative path"),
    ("Windows user profile absolute path", re.compile(WINDOWS_USERS, re.IGNORECASE), "a repository-relative path or an environment variable"),
    ("Linux home absolute path", re.compile(re.escape(POSIX_HOME)), ".codex/ or another repository-relative path"),
    ("macOS user absolute path", re.compile(re.escape(MAC_USERS)), ".codex/ or another repository-relative path"),
)


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if b"\0" in data:
        return None

    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def check_file(path: Path) -> list[str]:
    text = read_text(path)
    if text is None:
        return []

    failures: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for label, pattern, suggestion in RULES:
            match = pattern.search(line)
            if match:
                failures.append(
                    f"{path}:{line_number}: {label}: use {suggestion} instead"
                )
    return failures


def main(argv: list[str]) -> int:
    failures: list[str] = []
    for filename in argv:
        path = Path(filename)
        if path.is_file():
            failures.extend(check_file(path))

    if failures:
        print("Local absolute paths are not portable:")
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
