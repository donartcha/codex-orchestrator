from __future__ import annotations

import json

import pytest

from codex_context.orchestration import OrchestrationStore


@pytest.mark.orchestration
def test_record_task_builds_dependency_graph(tmp_path) -> None:
    store = OrchestrationStore(tmp_path / "orchestration")

    store.record_task("phase1", "run-1", files=("context.py",), status="done")
    store.record_task("phase2", "run-1", dependencies=("phase1",), files=("backends.py",))
    graph = store.get_task_graph("run-1")

    assert {task.task_id for task in graph.tasks} == {"phase1", "phase2"}
    assert graph.edges == (("phase1", "phase2"),)
    graph_file = tmp_path / "orchestration" / "graphs" / "run-1.json"
    assert graph_file.exists()
    assert json.loads(graph_file.read_text(encoding="utf-8"))["edges"] == [["phase1", "phase2"]]


@pytest.mark.orchestration
def test_validate_dependencies_reports_missing_and_failed_dependencies(tmp_path) -> None:
    store = OrchestrationStore(tmp_path / "orchestration")

    store.record_task("phase1", "run-1")
    store.record_task("phase2", "run-1", dependencies=("phase1", "missing"))
    store.record_validation("phase1", "pytest", False, "failed")

    result = store.validate_dependencies("phase2")

    assert result.ok is False
    assert result.missing_dependencies == ("missing",)
    assert result.pending_dependencies == ("phase1",)

    store.record_task("phase1", "run-1", status="done")
    result = store.validate_dependencies("phase2")
    assert result.failed_dependencies == ("phase1",)


@pytest.mark.orchestration
def test_validate_dependencies_requires_done_status_and_successful_validation(tmp_path) -> None:
    store = OrchestrationStore(tmp_path / "orchestration")

    store.record_task("phase1", "run-1", status="pending")
    store.record_task("phase2", "run-1", dependencies=("phase1",))
    assert store.validate_dependencies("phase2").ok is False

    store.record_task("phase1", "run-1", status="done")
    assert store.validate_dependencies("phase2").ok is False

    store.record_validation("phase1", "pytest", True, "ok")
    assert store.validate_dependencies("phase2").ok is True


@pytest.mark.orchestration
def test_detect_conflicts_persists_overlapping_write_scope(tmp_path) -> None:
    store = OrchestrationStore(tmp_path / "orchestration")

    store.record_task("worker-a", "run-1", files=("context.py", "tests.py"))
    store.record_task("worker-b", "run-1", files=("context.py",))
    conflicts = store.detect_conflicts(("worker-a", "worker-b"))

    assert len(conflicts) == 1
    assert conflicts[0].kind == "overlapping_write_scope"
    assert conflicts[0].task_ids == ("worker-a", "worker-b")
    assert (tmp_path / "orchestration" / "conflicts" / "conflict-1.json").exists()


@pytest.mark.orchestration
def test_record_ids_reject_path_traversal(tmp_path) -> None:
    store = OrchestrationStore(tmp_path / "orchestration")

    with pytest.raises(ValueError):
        store.record_task("../escape", "run-1")
    with pytest.raises(ValueError):
        store.record_task("phase1", "../escape")


@pytest.mark.orchestration
def test_orchestration_records_are_sanitized_before_persistence(tmp_path) -> None:
    store = OrchestrationStore(tmp_path / "orchestration")
    windows_profile = "C:" + "\\Users\\example"

    store.record_task(
        "phase1",
        "run-1",
        files=(windows_profile + r"\project\secret.txt",),
    )
    store.record_validation("phase1", "tool --token=abc123", True, "password=do-not-store")

    rendered = (tmp_path / "orchestration" / "tasks" / "phase1.json").read_text(encoding="utf-8")
    validation = (tmp_path / "orchestration" / "validations" / "phase1.json").read_text(encoding="utf-8")
    assert windows_profile not in rendered
    assert "abc123" not in validation
    assert "do-not-store" not in validation


@pytest.mark.orchestration
def test_consolidate_tasks_counts_statuses(tmp_path) -> None:
    store = OrchestrationStore(tmp_path / "orchestration")

    store.record_task("done", "run-1", status="done")
    store.record_task("pending", "run-1", status="pending")
    store.record_task("blocked", "run-1", status="blocked")

    result = store.consolidate_tasks(("done", "pending", "blocked"))

    assert result.total == 3
    assert result.completed == 1
    assert result.pending == 1
    assert result.blocked == 1
