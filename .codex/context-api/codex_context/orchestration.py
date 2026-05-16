from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


@dataclass(frozen=True)
class OrchestrationExecutionRecord:
    execution_id: str
    title: str
    description: str | None = None
    assigned_agent: str | None = None
    root_task_id: str = ""
    status: str = "pending"
    summary: str | None = None
    created_at: str = field(default_factory=lambda: _now())


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
    """Backend-backed orchestration service used behind CodexContext."""

    def __init__(self, backend: Any) -> None:
        self.backend = backend

    def start_execution(
        self,
        title: str,
        description: str,
        assigned_agent: str = "orchestrator",
    ) -> OrchestrationExecutionRecord:
        execution_id = self.next_execution_id()
        root_task_id = f"root-{execution_id}"
        self.record_task(task_id=root_task_id, execution_id=execution_id, status="pending")
        row = self.backend.remember_orchestration_execution(
            execution_id,
            title,
            description,
            assigned_agent,
            root_task_id,
            "pending",
            None,
        )
        return _execution_from_dict(row)

    def finish_execution(self, execution_id: str, summary: str, status: str = "done") -> OrchestrationExecutionRecord | None:
        _validate_record_id(str(execution_id), "execution_id")
        existing = self.backend.orchestration_execution(execution_id)
        if existing is None:
            return None
        row = self.backend.remember_orchestration_execution(
            execution_id,
            str(existing.get("title") or execution_id),
            existing.get("description"),
            existing.get("assigned_agent"),
            str(existing.get("root_task_id") or f"root-{execution_id}"),
            status,
            summary,
        )
        return _execution_from_dict(row)

    def next_execution_id(self) -> str:
        highest = 0
        for row in self.backend.orchestration_executions(limit=None):
            execution_id = str(row.get("execution_id") or "")
            match = re.fullmatch(r"exec-(\d+)", execution_id)
            if match:
                highest = max(highest, int(match.group(1)))
        return f"exec-{highest + 1:04d}"

    def next_phase_id(self, execution_id: str) -> str:
        _validate_record_id(str(execution_id), "execution_id")
        tasks = self.backend.orchestration_tasks(execution_id)
        phase_count = sum(1 for task in tasks if str(task.get("task_id") or "").startswith(f"phase-{execution_id}-"))
        return f"phase-{execution_id}-{phase_count + 1:03d}"

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
        _validate_task_payload(task_id, execution_id, parent_id, dependencies)
        row = self.backend.remember_orchestration_task(
            str(task_id),
            str(execution_id),
            str(parent_id) if parent_id is not None else None,
            list(str(item) for item in dependencies),
            list(str(item) for item in files),
            validation_command,
            status,
        )
        return _task_from_dict(row)

    def record_validation(self, task_id: str, command: str, success: bool, output: str = "") -> ValidationRecord:
        _validate_record_id(str(task_id), "task_id")
        return _validation_from_dict(
            self.backend.remember_orchestration_validation(str(task_id), command, bool(success), output)
        )

    def get_task(self, task_id: str) -> OrchestrationTaskRecord | None:
        _validate_record_id(str(task_id), "task_id")
        row = self.backend.orchestration_task(task_id)
        return _task_from_dict(row) if row is not None else None

    def get_task_graph(self, execution_id: str) -> TaskGraph:
        _validate_record_id(str(execution_id), "execution_id")
        tasks = tuple(_task_from_dict(row) for row in self.backend.orchestration_tasks(execution_id))
        edges = tuple(
            (dependency, task.task_id)
            for task in tasks
            for dependency in task.dependencies
        )
        return TaskGraph(execution_id, tasks, edges)

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
        execution_id = records[0].execution_id if records else None
        self.backend.replace_orchestration_conflicts(
            execution_id,
            [
                {"kind": conflict.kind, "task_ids": list(conflict.task_ids), "detail": conflict.detail}
                for conflict in conflicts
            ],
        )
        return conflicts

    def consolidate_tasks(self, task_ids: tuple[str, ...]) -> ConsolidationResult:
        records = [record for task_id in task_ids if (record := self.get_task(task_id)) is not None]
        completed = sum(1 for record in records if record.status == "done")
        blocked = sum(1 for record in records if record.status == "blocked")
        pending = sum(1 for record in records if record.status not in {"done", "blocked"})
        return ConsolidationResult(len(records), completed, pending, blocked)

    def _validation(self, task_id: str) -> ValidationRecord | None:
        _validate_record_id(str(task_id), "task_id")
        row = self.backend.orchestration_validation(task_id)
        return _validation_from_dict(row) if row is not None else None


def _execution_from_dict(data: dict[str, Any]) -> OrchestrationExecutionRecord:
    return OrchestrationExecutionRecord(
        execution_id=str(data["execution_id"]),
        title=str(data["title"]),
        description=data.get("description"),
        assigned_agent=data.get("assigned_agent"),
        root_task_id=str(data.get("root_task_id") or ""),
        status=str(data.get("status") or "pending"),
        summary=data.get("summary"),
        created_at=str(data.get("created_at") or _now()),
    )


def _task_from_dict(data: dict[str, Any]) -> OrchestrationTaskRecord:
    return OrchestrationTaskRecord(
        task_id=str(data["task_id"]),
        execution_id=str(data["execution_id"]),
        parent_id=data.get("parent_id"),
        dependencies=tuple(data.get("dependencies") or ()),
        files=tuple(data.get("files") or ()),
        validation_command=data.get("validation_command"),
        status=str(data.get("status") or "pending"),
        created_at=str(data.get("created_at") or _now()),
    )


def _validation_from_dict(data: dict[str, Any]) -> ValidationRecord:
    return ValidationRecord(
        task_id=str(data["task_id"]),
        command=str(data["command"]),
        success=bool(data["success"]),
        output=str(data.get("output") or ""),
        created_at=str(data.get("created_at") or _now()),
    )


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_task_payload(
    task_id: str,
    execution_id: str,
    parent_id: str | None,
    dependencies: tuple[str, ...],
) -> None:
    _validate_record_id(str(task_id), "task_id")
    _validate_record_id(str(execution_id), "execution_id")
    if parent_id is not None:
        _validate_record_id(str(parent_id), "parent_id")
    for dependency in dependencies:
        _validate_record_id(str(dependency), "dependency")


def _validate_record_id(value: str, field_name: str) -> None:
    if not SAFE_ID.fullmatch(value):
        raise ValueError(f"{field_name} must be a safe identifier.")
