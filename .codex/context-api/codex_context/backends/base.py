from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from ..models import ArchitecturalDecision, CommandHistory, ContextSnapshot, LessonLearned, Task, TaskLog


@dataclass(frozen=True)
class BackendStatus:
    name: str
    active: bool
    degraded: bool = False
    warning: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContextBackend(Protocol):
    status: BackendStatus

    def close(self) -> None: ...

    @contextmanager
    def session(self) -> Iterator[Session]: ...

    def remember_task(
        self,
        title: str,
        description: str,
        assigned_agent: str | None,
        priority: str,
        parent_task_id: int | None = None,
        task_kind: str = "task",
        sort_order: int = 0,
        depends_on: list[int] | None = None,
        acceptance_criteria: str | None = None,
    ) -> Task: ...

    def tasks(self, status: str | None = "pending", limit: int | None = None) -> list[Task]: ...
    def task_children(self, parent_task_id: int, limit: int | None = None) -> list[Task]: ...
    def task_tree(self, root_task_id: int) -> dict[str, object] | None: ...
    def update_task(self, task_id: int, **fields: Any) -> Task | None: ...
    def reorder_task(self, task_id: int, sort_order: int) -> Task | None: ...
    def recompute_parent_status(self, parent_task_id: int) -> Task | None: ...

    def set_task_status(self, task_id: int, status: str) -> Task | None: ...

    def remember_snapshot(
        self,
        snapshot_type: str,
        title: str | None,
        content: str,
        tags: dict | list | None,
        task_id: int | None = None,
    ) -> ContextSnapshot: ...

    def snapshots(self, limit: int | None = None, task_id: int | None = None) -> list[ContextSnapshot]: ...

    def remember_task_log(self, task_id: int, content: str, agent_name: str | None, log_type: str) -> TaskLog: ...

    def task_logs(
        self,
        task_id: int | None = None,
        agent_name: str | None = None,
        log_type: str | None = None,
        limit: int = 20,
    ) -> list[TaskLog]: ...

    def remember_orchestration_execution(
        self,
        execution_id: str,
        title: str,
        description: str | None,
        assigned_agent: str | None,
        root_task_id: str,
        status: str,
        summary: str | None = None,
    ) -> dict[str, object]: ...

    def orchestration_executions(self, limit: int | None = None) -> list[dict[str, object]]: ...

    def orchestration_execution(self, execution_id: str) -> dict[str, object] | None: ...

    def remember_orchestration_task(
        self,
        task_id: str,
        execution_id: str,
        parent_id: str | None,
        dependencies: list[str],
        files: list[str],
        validation_command: str | None,
        status: str,
    ) -> dict[str, object]: ...

    def orchestration_task(self, task_id: str) -> dict[str, object] | None: ...

    def orchestration_tasks(self, execution_id: str | None = None) -> list[dict[str, object]]: ...

    def remember_orchestration_validation(
        self,
        task_id: str,
        command: str,
        success: bool,
        output: str,
    ) -> dict[str, object]: ...

    def orchestration_validation(self, task_id: str) -> dict[str, object] | None: ...

    def replace_orchestration_conflicts(
        self,
        execution_id: str | None,
        conflicts: list[dict[str, object]],
    ) -> list[dict[str, object]]: ...

    def remember_decision(
        self,
        decision_key: str,
        title: str,
        rationale: str,
        consequences: str,
        task_id: int | None = None,
    ) -> ArchitecturalDecision: ...

    def decisions(
        self,
        status: str | None = None,
        limit: int | None = None,
        task_id: int | None = None,
    ) -> list[ArchitecturalDecision]: ...

    def supersede_decision(self, old_id: int, new_id: int) -> ArchitecturalDecision | None: ...

    def remember_command(
        self,
        agent_name: str,
        shell_type: str,
        command_text: str,
        success_flag: bool,
        error_message: str | None = None,
        correction_applied: str | None = None,
        task_id: int | None = None,
    ) -> CommandHistory: ...

    def commands(
        self,
        limit: int = 20,
        success_flag: bool | None = None,
        task_id: int | None = None,
    ) -> list[CommandHistory]: ...

    def remember_lesson(
        self,
        category: str,
        problem_description: str,
        solution_description: str,
        prevention_strategy: str,
        task_id: int | None = None,
    ) -> LessonLearned: ...

    def lessons(
        self,
        category: str | None = None,
        limit: int | None = None,
        task_id: int | None = None,
    ) -> list[LessonLearned]: ...
    def remember_lesson_category(self, key_name: str, title: str, description: str | None = None, parent_key: str | None = None): ...
    def lesson_categories(self, status: str | None = "active", limit: int | None = 100): ...
    def find_lesson_categories(self, query: str, limit: int = 10): ...
