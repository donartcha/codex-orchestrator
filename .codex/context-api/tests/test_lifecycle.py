from __future__ import annotations

import subprocess

import pytest

from codex_context.backends import FileBackend
from codex_context.context import open_context


@pytest.mark.lifecycle
def test_snapshot_add_and_list_through_facade_uses_sanitized_content(tmp_path) -> None:
    backend = FileBackend(path=tmp_path / "memory.json")
    windows_profile = "C:" + "\\Users\\example"

    with open_context(backend=backend) as context:
        context.remember_task("Snapshot me", "password=do-not-store", "testing-agent")
        snapshot = context.remember_snapshot(
            title="safe snapshot password=do-not-store",
            limit=10,
            tags={"path": windows_profile + r"\project"},
        )
        snapshots = context.snapshots(limit=10)

    assert "do-not-store" not in snapshot.title
    assert "[REDACTED]" in snapshot.title
    assert windows_profile not in repr(snapshot.tags)
    assert snapshots[0].id == snapshot.id
    assert "do-not-store" not in snapshot.content
    assert "[REDACTED]" in snapshot.content


@pytest.mark.lifecycle
def test_supersede_decision_marks_old_decision_inactive(tmp_path) -> None:
    backend = FileBackend(path=tmp_path / "memory.json")

    with open_context(backend=backend) as context:
        old = context.remember_decision("old-key", "Old", "Old rationale", "Old consequences")
        new = context.remember_decision("new-key", "New", "New rationale", "New consequences")
        updated = context.supersede_decision(old.id, new.id)
        active = context.decisions(status="active", limit=10)

    assert updated is not None
    assert updated.status == "superseded"
    assert "Superseded by decision" in updated.consequences
    assert {decision.id for decision in active} == {new.id}


@pytest.mark.lifecycle
def test_decision_key_uniqueness_is_enforced_in_file_backend(tmp_path) -> None:
    backend = FileBackend(path=tmp_path / "memory.json")

    with open_context(backend=backend) as context:
        context.remember_decision("unique-key", "First", "Rationale", "")
        # Attempting to create a second decision with same key should raise ValueError
        with pytest.raises(ValueError, match="already exists and is active"):
            context.remember_decision("unique-key", "Second", "Rationale", "")


@pytest.mark.lifecycle
def test_lifecycle_cli_commands_use_isolated_file_backend(cli_command, context_api_root, isolated_context_env) -> None:
    isolated_context_env["CODEX_CONTEXT_DISABLE_SQLITE"] = "1"

    add_task = subprocess.run(
        [
            *cli_command,
            "task",
            "add",
            "--title",
            "Lifecycle CLI task",
            "--description",
            "token=do-not-store",
        ],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    add_snapshot = subprocess.run(
        [*cli_command, "snapshot", "add", "--title", "cli snapshot", "--limit", "5"],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    list_snapshot = subprocess.run(
        [*cli_command, "snapshot", "list", "--limit", "5"],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    compact = subprocess.run(
        [*cli_command, "memory", "compact"],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    contradictions = subprocess.run(
        [*cli_command, "contradictions", "list"],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )

    assert add_task.returncode == 0, add_task.stderr
    assert add_snapshot.returncode == 0, add_snapshot.stderr
    assert list_snapshot.returncode == 0, list_snapshot.stderr
    assert compact.returncode == 0, compact.stderr
    assert contradictions.returncode == 0, contradictions.stderr
    assert "cli snapshot" in list_snapshot.stdout
    assert "do-not-store" not in list_snapshot.stdout
    assert "no destructive compaction was run" in compact.stdout


@pytest.mark.lifecycle
def test_snapshot_restore_is_blocked_until_restore_plan_is_approved(cli_command, context_api_root, isolated_context_env) -> None:
    result = subprocess.run(
        [*cli_command, "snapshot", "restore", "1"],
        cwd=context_api_root,
        env=isolated_context_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )

    assert result.returncode == 2
    assert "not enabled" in result.stdout
