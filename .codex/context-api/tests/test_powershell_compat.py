from __future__ import annotations

import pytest


SAFE_COMMANDS = [
    r"Set-Location .codex\context-api",
    r".\.venv\Scripts\python.exe codex_memory.py bootstrap --limit 5",
    r".\.venv\Scripts\python.exe -m pytest tests",
    r"Get-ChildItem -LiteralPath codex_context -Recurse -Filter *.py",
]

UNSAFE_COMMANDS = [
    r"python -m py_compile codex_context/**/*.py",
    r"wsl bash -c ""cd /mnt/.../codex/context-api && python codex_memory.py bootstrap""",
    r"& '.\.codex\context-api\codex_memory.py' bootstrap",
]


def _powershell_command_risks(command: str) -> list[str]:
    risks: list[str] = []
    if "&&" in command:
        risks.append("bash command chaining")
    if "/mnt/..." in command:
        risks.append("placeholder WSL path")
    if "**/*.py" in command or "**\\*.py" in command:
        risks.append("recursive glob passed to Python")
    if "codex_memory.py' bootstrap" in command or 'codex_memory.py" bootstrap' in command:
        risks.append("direct .py invocation")
    return risks


@pytest.mark.powershell
def test_recommended_commands_have_no_known_powershell_risks() -> None:
    for command in SAFE_COMMANDS:
        assert _powershell_command_risks(command) == []


@pytest.mark.powershell
def test_problematic_markdown_commands_are_detected() -> None:
    detected = [_powershell_command_risks(command) for command in UNSAFE_COMMANDS]

    assert all(risks for risks in detected)
