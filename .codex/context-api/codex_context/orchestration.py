from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .sanitizer import sanitize_memory


CONTEXT_API_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ORCHESTRATION_ROOT = CONTEXT_API_ROOT / "orchestration"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


@dataclass(frozen=True)
class OrchestrationTaskRecord:
    task_id: str
    execution_id: str
    parent_id: str | None = None
    dependencies: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
    validation_command: str | None = None
    status: str = "pending"
    created_at: str = field(default_factory=lambda: _now())


@dataclass(frozen=True)
class ValidationRecord:
    task_id: str
    command: str
    success: bool
    output: str = ""
    created_at: str = field(default_factory=lambda: _now())


@dataclass(frozen=True)
class TaskGraph:
    execution_id: str
    tasks: tuple[OrchestrationTaskRecord, ...]
    edges: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ValidationResult:
    task_id: str
    ok: bool
    missing_dependencies: tuple[str, ...] = ()
    failed_dependencies: tuple[str, ...] = ()
    pending_dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class Conflict:
    kind: str
    task_ids: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class ConsolidationResult:
    total: int
    completed: int
    pending: int
    blocked: int


class OrchestrationStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or DEFAULT_ORCHESTRATION_ROOT)
        self.tasks_dir = self.root / "tasks"
        self.graphs_dir = self.root / "graphs"
        self.validations_dir = self.root / "validations"
        self.conflicts_dir = self.root / "conflicts"
        for directory in (self.tasks_dir, self.graphs_dir, self.validations_dir, self.conflicts_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def record_task(
        self,
        task_id: str,
        execution_id: str,
        parent_id: str | None = None,
        dependencies: tuple[str, ...] = (),
        files: tuple[str, ...] = (),
        validation_command: str | None = None,
        status: str = "pending",
    ) -> OrchestrationTaskRecord:
        _validate_record_id(str(task_id), "task_id")
        _validate_record_id(str(execution_id), "execution_id")
        if parent_id is not None:
            _validate_record_id(str(parent_id), "parent_id")
        for dependency in dependencies:
            _validate_record_id(str(dependency), "dependency")
        record = OrchestrationTaskRecord(
            task_id=str(task_id),
            execution_id=str(execution_id),
            parent_id=str(parent_id) if parent_id is not None else None,
            dependencies=tuple(str(item) for item in dependencies),
            files=tuple(str(item) for item in files),
            validation_command=validation_command,
            status=status,
        )
        self._write_json(_safe_child_path(self.tasks_dir, record.task_id), asdict(record))
        self._write_graph(record.execution_id)
        return record

    def record_validation(self, task_id: str, command: str, success: bool, output: str = "") -> ValidationRecord:
        _validate_record_id(str(task_id), "task_id")
        record = ValidationRecord(str(task_id), command, bool(success), output)
        self._write_json(_safe_child_path(self.validations_dir, record.task_id), asdict(record))
        return record

    def get_task(self, task_id: str) -> OrchestrationTaskRecord | None:
        _validate_record_id(str(task_id), "task_id")
        path = _safe_child_path(self.tasks_dir, task_id)
        if not path.exists():
            return None
        return _task_from_dict(self._read_json(path))

    def get_task_graph(self, execution_id: str) -> TaskGraph:
        _validate_record_id(str(execution_id), "execution_id")
        tasks = tuple(task for task in self._tasks() if task.execution_id == execution_id)
        edges = tuple(
            (dependency, task.task_id)
            for task in tasks
            for dependency in task.dependencies
        )
        graph = TaskGraph(execution_id, tasks, edges)
        self._write_json(_safe_child_path(self.graphs_dir, execution_id), _graph_to_dict(graph))
        return graph

    def validate_dependencies(self, task_id: str) -> ValidationResult:
        task = self.get_task(task_id)
        if task is None:
            return ValidationResult(task_id, False, missing_dependencies=(task_id,))
        missing: list[str] = []
        failed: list[str] = []
        pending: list[str] = []
        for dependency in task.dependencies:
            dependency_task = self.get_task(dependency)
            if dependency_task is None:
                missing.append(dependency)
                continue
            if dependency_task.status != "done":
                pending.append(dependency)
                continue
            validation = self._validation(dependency)
            if validation is None or not validation.success:
                failed.append(dependency)
        return ValidationResult(task_id, not missing and not failed and not pending, tuple(missing), tuple(failed), tuple(pending))

    def detect_conflicts(self, task_ids: tuple[str, ...]) -> list[Conflict]:
        records = [record for task_id in task_ids if (record := self.get_task(task_id)) is not None]
        by_file: dict[str, list[str]] = {}
        for record in records:
            for path in record.files:
                by_file.setdefault(path, []).append(record.task_id)
        conflicts = [
            Conflict("overlapping_write_scope", tuple(ids), f"Multiple tasks write {path}.")
            for path, ids in by_file.items()
            if len(ids) > 1
        ]
        for index, conflict in enumerate(conflicts, start=1):
            self._write_json(_safe_child_path(self.conflicts_dir, f"conflict-{index}"), asdict(conflict))
        return conflicts

    def consolidate_tasks(self, task_ids: tuple[str, ...]) -> ConsolidationResult:
        records = [record for task_id in task_ids if (record := self.get_task(task_id)) is not None]
        completed = sum(1 for record in records if record.status == "done")
        blocked = sum(1 for record in records if record.status == "blocked")
        pending = sum(1 for record in records if record.status not in {"done", "blocked"})
        return ConsolidationResult(len(records), completed, pending, blocked)

    def _tasks(self) -> tuple[OrchestrationTaskRecord, ...]:
        return tuple(_task_from_dict(self._read_json(path)) for path in sorted(self.tasks_dir.glob("*.json")))

    def _validation(self, task_id: str) -> ValidationRecord | None:
        _validate_record_id(str(task_id), "task_id")
        path = _safe_child_path(self.validations_dir, task_id)
        if not path.exists():
            return None
        data = self._read_json(path)
        return ValidationRecord(
            task_id=str(data["task_id"]),
            command=str(data["command"]),
            success=bool(data["success"]),
            output=str(data.get("output") or ""),
            created_at=str(data["created_at"]),
        )

    def _write_graph(self, execution_id: str) -> None:
        graph = self.get_task_graph(execution_id)
        self._write_json(_safe_child_path(self.graphs_dir, execution_id), _graph_to_dict(graph))

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        sanitized, _report = sanitize_memory(payload, repo_root=CONTEXT_API_ROOT.parents[1])
        path.write_text(json.dumps(sanitized, indent=2, ensure_ascii=False), encoding="utf-8")


def record_task(*args, **kwargs) -> OrchestrationTaskRecord:
    return OrchestrationStore().record_task(*args, **kwargs)


def get_task_graph(execution_id: str) -> TaskGraph:
    return OrchestrationStore().get_task_graph(execution_id)


def validate_dependencies(task_id: str) -> ValidationResult:
    return OrchestrationStore().validate_dependencies(task_id)


def detect_conflicts(task_ids: tuple[str, ...]) -> list[Conflict]:
    return OrchestrationStore().detect_conflicts(task_ids)


def consolidate_tasks(task_ids: tuple[str, ...]) -> ConsolidationResult:
    return OrchestrationStore().consolidate_tasks(task_ids)


def _task_from_dict(data: dict[str, Any]) -> OrchestrationTaskRecord:
    return OrchestrationTaskRecord(
        task_id=str(data["task_id"]),
        execution_id=str(data["execution_id"]),
        parent_id=data.get("parent_id"),
        dependencies=tuple(data.get("dependencies") or ()),
        files=tuple(data.get("files") or ()),
        validation_command=data.get("validation_command"),
        status=str(data.get("status") or "pending"),
        created_at=str(data["created_at"]),
    )


def _graph_to_dict(graph: TaskGraph) -> dict[str, Any]:
    return {
        "execution_id": graph.execution_id,
        "tasks": [asdict(task) for task in graph.tasks],
        "edges": [list(edge) for edge in graph.edges],
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_record_id(value: str, field_name: str) -> None:
    if not SAFE_ID.fullmatch(value):
        raise ValueError(f"{field_name} must be a safe identifier.")


def _safe_child_path(directory: Path, identifier: str) -> Path:
    _validate_record_id(str(identifier), "identifier")
    path = (directory / f"{identifier}.json").resolve()
    root = directory.resolve()
    if root not in path.parents:
        raise ValueError("record path escaped its storage directory.")
    return path
