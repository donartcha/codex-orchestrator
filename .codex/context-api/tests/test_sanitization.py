from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from codex_context.backends import FileBackend
from codex_context.context import open_context
from codex_context.sanitizer import detect_secrets, normalize_paths, sanitize_memory


@pytest.mark.sanitization
def test_sanitize_memory_redacts_secret_values_without_preserving_original() -> None:
    payload = {
        "command": "mysql -u root -pMyPassword123",
        "description": "password=super-secret api_key=abc123 token=xyz",
    }

    sanitized, report = sanitize_memory(payload)

    rendered = repr(sanitized)
    assert "MyPassword123" not in rendered
    assert "super-secret" not in rendered
    assert "abc123" not in rendered
    assert "xyz" not in rendered
    assert "[REDACTED]" in rendered
    assert report.changed
    assert all("secret" not in repr(event).lower() for event in report.events)


@pytest.mark.sanitization
def test_sanitize_memory_does_not_redact_hyphenated_words_as_mysql_password_flags() -> None:
    sanitized, report = sanitize_memory({"decision_key": "phase5-restore-blocked-until-backup-plan"})

    assert sanitized["decision_key"] == "phase5-restore-blocked-until-backup-plan"
    assert not report.changed


@pytest.mark.sanitization
def test_detect_secrets_reports_metadata_only() -> None:
    events = detect_secrets({"command": "token=abc123"})

    assert events
    assert events[0].field_path == "$.command"
    assert events[0].kind == "token"
    assert "abc123" not in repr(events)


@pytest.mark.sanitization
def test_normalize_paths_redacts_local_absolute_paths(tmp_path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    windows_profile = "C:" + "\\Users\\example"
    linux_home = "/" + "home/example"
    payload = {
        "repo_path": str(repo_root / ".codex" / "context-api"),
        "windows_path": windows_profile + r"\project\.env",
        "unix_path": linux_home + "/project/.env",
    }

    sanitized = normalize_paths(payload, repo_root)
    rendered = repr(sanitized)

    assert str(repo_root) not in rendered
    assert windows_profile not in rendered
    assert linux_home not in rendered
    assert "${REPO_ROOT}" in rendered or "[REDACTED_PATH]" in rendered


@pytest.mark.sanitization
def test_open_context_sanitizes_writes_through_facade(tmp_path) -> None:
    backend = FileBackend(path=tmp_path / "memory.json")

    with open_context(backend=backend) as context:
        task = context.remember_task(
            "Check sanitizer",
            "password=do-not-store C:\\Users\\example\\project",
            "implementation-agent",
        )
        command = context.remember_command(
            "testing-agent",
            "powershell",
            "tool --token=abc123",
            False,
            "api_key=hidden",
        )

    assert "do-not-store" not in task.description
    assert "C:\\Users\\example" not in task.description
    assert "abc123" not in command.command_text
    assert "hidden" not in command.error_message


@pytest.mark.sanitization
def test_cli_task_add_sanitizes_file_fallback_writes(cli_command, context_api_root, isolated_context_env) -> None:
    isolated_context_env["CODEX_CONTEXT_DISABLE_SQLITE"] = "1"

    add_result = subprocess.run(
        [
            *cli_command,
            "task",
            "add",
            "--title",
            "Sanitize via CLI",
            "--description",
            "password=do-not-store",
            "--agent",
            "testing-agent",
        ],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    list_result = subprocess.run(
        [*cli_command, "task", "list", "--limit", "5"],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )

    assert add_result.returncode == 0, add_result.stderr
    assert list_result.returncode == 0, list_result.stderr
    persisted_memory = Path(isolated_context_env["CODEX_CONTEXT_FILE_PATH"]).read_text(encoding="utf-8")
    assert "do-not-store" not in persisted_memory
    assert "[REDACTED]" in persisted_memory
    assert "do-not-store" not in list_result.stdout
