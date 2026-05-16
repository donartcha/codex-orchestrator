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


@pytest.mark.cli
def test_orchestration_start_and_status_work_through_cli(cli_command, context_api_root, isolated_context_env) -> None:
    """Test orchestration CLI commands: start and status."""
    isolated_context_env["CODEX_CONTEXT_DISABLE_MARIADB"] = "1"
    isolated_context_env["CODEX_CONTEXT_DISABLE_SQLITE"] = "1"

    start_result = _run_cli(
        cli_command,
        context_api_root,
        isolated_context_env,
        "orchestrate",
        "start",
        "--title",
        "Test Orchestration",
        "--description",
        "Validate orchestration CLI integration.",
        "--agent",
        "testing-agent",
    )

    assert start_result.returncode == 0, start_result.stderr
    assert "Orchestration started" in start_result.stdout
    assert "execution_id=" in start_result.stdout

    # Extract execution_id from output for status check
    import re
    match = re.search(r"execution_id=(\S+)", start_result.stdout)
    if match:
        execution_id = match.group(1)
        status_result = _run_cli(
            cli_command,
            context_api_root,
            isolated_context_env,
            "orchestrate",
            "status",
            "--execution-id",
            execution_id,
        )
        assert status_result.returncode == 0, status_result.stderr
        assert "Orchestration status:" in status_result.stdout
        assert "Total tasks:" in status_result.stdout


@pytest.mark.cli
def test_orchestration_phase_and_validation_work_through_cli(cli_command, context_api_root, isolated_context_env) -> None:
    """Test orchestration CLI commands: phase and validation."""
    isolated_context_env["CODEX_CONTEXT_DISABLE_MARIADB"] = "1"
    isolated_context_env["CODEX_CONTEXT_DISABLE_SQLITE"] = "1"

    # Start orchestration
    start_result = _run_cli(
        cli_command,
        context_api_root,
        isolated_context_env,
        "orchestrate",
        "start",
        "--title",
        "Phase Test",
        "--description",
        "Test phase and validation commands.",
    )
    assert start_result.returncode == 0, start_result.stderr
    import re
    match = re.search(r"execution_id=(\S+)", start_result.stdout)
    assert match, "Could not extract execution_id from start output"
    execution_id = match.group(1)

    # Add a phase
    phase_result = _run_cli(
        cli_command,
        context_api_root,
        isolated_context_env,
        "orchestrate",
        "phase",
        "--execution-id",
        execution_id,
        "--title",
        "Phase 1",
        "--agent",
        "implementation-agent",
    )
    assert phase_result.returncode == 0, phase_result.stderr
    assert "Phase added" in phase_result.stdout
    assert "task_id=" in phase_result.stdout

    # Extract task_id from phase output
    match = re.search(r"task_id=(\S+)", phase_result.stdout)
    assert match, "Could not extract task_id from phase output"
    task_id = match.group(1)

    # Record validation
    validation_result = _run_cli(
        cli_command,
        context_api_root,
        isolated_context_env,
        "orchestrate",
        "validation",
        "--execution-id",
        execution_id,
        "--task-id",
        task_id,
        "--command",
        "pytest tests",
        "--status",
        "passed",
        "--output",
        "5 passed in 1.23s",
    )
    assert validation_result.returncode == 0, validation_result.stderr
    assert "Validation recorded" in validation_result.stdout
