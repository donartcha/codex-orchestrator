from __future__ import annotations

import subprocess

import pytest


def _run_cli(cli_command: list[str], context_api_root, isolated_context_env, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*cli_command, *args],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


@pytest.mark.cli
def test_backend_status_uses_file_fallback_when_sql_backends_disabled(cli_command, context_api_root, isolated_context_env) -> None:
    isolated_context_env["CODEX_CONTEXT_DISABLE_MARIADB"] = "1"
    isolated_context_env["CODEX_CONTEXT_DISABLE_SQLITE"] = "1"

    result = _run_cli(cli_command, context_api_root, isolated_context_env, "backend-status")

    assert result.returncode == 0, result.stderr
    assert "Active backend: file" in result.stdout
    assert "Degraded: True" in result.stdout


@pytest.mark.cli
def test_task_add_and_list_use_isolated_file_fallback(cli_command, context_api_root, isolated_context_env) -> None:
    isolated_context_env["CODEX_CONTEXT_DISABLE_MARIADB"] = "1"
    isolated_context_env["CODEX_CONTEXT_DISABLE_SQLITE"] = "1"

    add_result = _run_cli(
        cli_command,
        context_api_root,
        isolated_context_env,
        "task",
        "add",
        "--title",
        "CLI isolated task",
        "--description",
        "Created in a temp file backend.",
        "--agent",
        "testing-agent",
    )
    list_result = _run_cli(cli_command, context_api_root, isolated_context_env, "task", "list", "--limit", "5")

    assert add_result.returncode == 0, add_result.stderr
    assert list_result.returncode == 0, list_result.stderr
    assert "CLI isolated task" in list_result.stdout
