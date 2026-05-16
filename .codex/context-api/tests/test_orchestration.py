from __future__ import annotations

import json

import pytest

from codex_context.backends import FileBackend, SQLiteBackend
from codex_context.context import open_context
from codex_context.orchestration import OrchestrationStore


def _file_store(tmp_path):
    backend = FileBackend(path=tmp_path / "memory.json")
    return backend, OrchestrationStore(backend)


@pytest.mark.orchestration
def test_record_task_builds_dependency_graph(tmp_path) -> None:
    backend, store = _file_store(tmp_path)

    try:
        store.record_task("phase1", "run-1", files=("context.py",), status="done")
        store.record_task("phase2", "run-1", dependencies=("phase1",), files=("backends.py",))
        graph = store.get_task_graph("run-1")
    finally:
        backend.close()

    assert {task.task_id for task in graph.tasks} == {"phase1", "phase2"}
    assert graph.edges == (("phase1", "phase2"),)
    fallback = json.loads((tmp_path / "memory.json").read_text(encoding="utf-8"))
    assert {task["task_id"] for task in fallback["orchestration_tasks"]} == {"phase1", "phase2"}
    assert not (tmp_path / "orchestration").exists()


@pytest.mark.orchestration
def test_validate_dependencies_reports_missing_and_failed_dependencies(tmp_path) -> None:
    backend, store = _file_store(tmp_path)

    try:
        store.record_task("phase1", "run-1")
        store.record_task("phase2", "run-1", dependencies=("phase1", "missing"))
        store.record_validation("phase1", "pytest", False, "failed")

        result = store.validate_dependencies("phase2")

        assert result.ok is False
        assert result.missing_dependencies == ("missing",)
        assert result.pending_dependencies == ("phase1",)

        store.record_task("phase1", "run-1", status="done")
        result = store.validate_dependencies("phase2")
    finally:
        backend.close()
    assert result.failed_dependencies == ("phase1",)


@pytest.mark.orchestration
def test_validate_dependencies_requires_done_status_and_successful_validation(tmp_path) -> None:
    backend, store = _file_store(tmp_path)

    try:
        store.record_task("phase1", "run-1", status="pending")
        store.record_task("phase2", "run-1", dependencies=("phase1",))
        assert store.validate_dependencies("phase2").ok is False

        store.record_task("phase1", "run-1", status="done")
        assert store.validate_dependencies("phase2").ok is False

        store.record_validation("phase1", "pytest", True, "ok")
        assert store.validate_dependencies("phase2").ok is True
    finally:
        backend.close()


@pytest.mark.orchestration
def test_detect_conflicts_persists_overlapping_write_scope(tmp_path) -> None:
    backend, store = _file_store(tmp_path)

    try:
        store.record_task("worker-a", "run-1", files=("context.py", "tests.py"))
        store.record_task("worker-b", "run-1", files=("context.py",))
        conflicts = store.detect_conflicts(("worker-a", "worker-b"))
        fallback = json.loads((tmp_path / "memory.json").read_text(encoding="utf-8"))
    finally:
        backend.close()

    assert len(conflicts) == 1
    assert conflicts[0].kind == "overlapping_write_scope"
    assert conflicts[0].task_ids == ("worker-a", "worker-b")
    assert fallback["orchestration_conflicts"][0]["kind"] == "overlapping_write_scope"


@pytest.mark.orchestration
def test_record_ids_reject_path_traversal(tmp_path) -> None:
    backend, store = _file_store(tmp_path)

    try:
        with pytest.raises(ValueError):
            store.record_task("../escape", "run-1")
        with pytest.raises(ValueError):
            store.record_task("phase1", "../escape")
    finally:
        backend.close()


@pytest.mark.orchestration
def test_orchestration_records_are_sanitized_before_persistence(tmp_path) -> None:
    backend = FileBackend(path=tmp_path / "memory.json")
    windows_profile = "C:" + "\\Users\\example"

    try:
        with open_context(backend=backend) as context:
            context.remember_orchestration_task(
                "phase1",
                "run-1",
                files=(windows_profile + r"\project\secret.txt",),
            )
            context.remember_orchestration_validation("phase1", "tool --token=abc123", True, "password=do-not-store")
    finally:
        backend.close()

    rendered = (tmp_path / "memory.json").read_text(encoding="utf-8")
    validation = rendered
    assert windows_profile not in rendered
    assert "abc123" not in validation
    assert "do-not-store" not in validation


@pytest.mark.orchestration
def test_consolidate_tasks_counts_statuses(tmp_path) -> None:
    backend, store = _file_store(tmp_path)

    try:
        store.record_task("done", "run-1", status="done")
        store.record_task("pending", "run-1", status="pending")
        store.record_task("blocked", "run-1", status="blocked")

        result = store.consolidate_tasks(("done", "pending", "blocked"))
    finally:
        backend.close()

    assert result.total == 3
    assert result.completed == 1
    assert result.pending == 1
    assert result.blocked == 1


@pytest.mark.orchestration
def test_orchestration_uses_sqlite_backend_without_json_side_path(tmp_path) -> None:
    backend = SQLiteBackend(path=tmp_path / "memory.sqlite3")
    try:
        store = OrchestrationStore(backend)
        execution = store.start_execution("SQL orchestration", "Stored through backend.", "testing-agent")
        store.record_task("phase1", execution.execution_id, dependencies=(execution.root_task_id,))
        graph = store.get_task_graph(execution.execution_id)
    finally:
        backend.close()

    assert execution.execution_id == "exec-0001"
    assert {task.task_id for task in graph.tasks} == {execution.root_task_id, "phase1"}
    assert not (tmp_path / "orchestration").exists()
