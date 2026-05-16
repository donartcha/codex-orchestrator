from __future__ import annotations

import subprocess
import sys

import pytest


def _run_script(context_api_root, isolated_context_env, script_name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(context_api_root / "scripts" / script_name), *args],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


@pytest.mark.cli
def test_official_cli_help_exposes_consolidated_commands(cli_command, context_api_root, isolated_context_env) -> None:
    result = subprocess.run(
        [*cli_command, "--help"],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    for command_name in ("bootstrap", "backend-status", "snapshot", "memory", "contradictions"):
        assert command_name in result.stdout


@pytest.mark.cli
def test_legacy_check_connection_uses_isolated_context(context_api_root, isolated_context_env) -> None:
    isolated_context_env["CODEX_CONTEXT_DISABLE_SQLITE"] = "1"

    result = _run_script(context_api_root, isolated_context_env, "check_connection.py")

    assert result.returncode == 0, result.stderr
    assert "Connection OK" in result.stdout


@pytest.mark.cli
def test_legacy_task_scripts_remain_compatible_with_file_fallback(context_api_root, isolated_context_env) -> None:
    isolated_context_env["CODEX_CONTEXT_DISABLE_SQLITE"] = "1"

    add_result = _run_script(
        context_api_root,
        isolated_context_env,
        "add_task.py",
        "Legacy task",
        "Created by legacy script",
        "--assigned-agent",
        "testing-agent",
    )
    list_result = _run_script(context_api_root, isolated_context_env, "list_tasks.py")

    assert add_result.returncode == 0, add_result.stderr
    assert list_result.returncode == 0, list_result.stderr
    assert "Legacy task" in list_result.stdout
