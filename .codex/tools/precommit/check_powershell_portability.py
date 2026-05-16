#!/usr/bin/env python
"""Reject accidental Bash-only commands in portable project text."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SKIP_SUFFIXES = {".sh", ".bash"}

RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"(?<![\w.-])mkdir\s+-p(?![\w.-])"), "mkdir " + "-p", "New-Item -ItemType Directory -Force"),
    (re.compile(r"(?<![\w.-])rm\s+-rf(?![\w.-])"), "rm " + "-rf", "Remove-Item -Recurse -Force"),
    (
        re.compile(r"(?<![\w./-])source\s+\.venv/bin/activate(?![\w./-])"),
        "source " + ".venv/bin/activate",
        r".\.venv\Scripts\Activate.ps1",
    ),
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
    if path.suffix.lower() in SKIP_SUFFIXES:
        return []

    text = read_text(path)
    if text is None:
        return []

    failures: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern, rejected, suggestion in RULES:
            if pattern.search(line):
                failures.append(
                    f"{path}:{line_number}: replace '{rejected}' with '{suggestion}' for PowerShell portability"
                )
    return failures


def main(argv: list[str]) -> int:
    failures: list[str] = []
    for filename in argv:
        path = Path(filename)
        if path.is_file():
            failures.extend(check_file(path))

    if failures:
        print("Accidental Bash commands found in portable project text:")
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
