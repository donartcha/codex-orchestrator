from __future__ import annotations

import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import (
    ArchitecturalDecision,
    CommandHistory,
    ContextSnapshot,
    LessonLearned,
    OrchestrationConflict,
    OrchestrationExecution,
    OrchestrationTask,
    OrchestrationValidation,
    Task,
    TaskLog,
)


def add_task(
    session: Session,
    title: str,
    description: str,
    assigned_agent: str | None,
    priority: str,
    parent_task_id: int | None = None,
    task_kind: str = "task",
    sort_order: int = 0,
    depends_on: list[int] | None = None,
    acceptance_criteria: str | None = None,
) -> Task:
    _validate_task_kind(task_kind)
    _validate_sort_order(sort_order)
    _validate_parent_task(session, parent_task_id)
    serialized_depends = _serialize_depends_on(depends_on)
    task = Task(
        title=title,
        description=description,
        assigned_agent=assigned_agent,
        priority=priority,
        parent_task_id=parent_task_id,
        task_kind=task_kind,
        sort_order=sort_order,
        depends_on=serialized_depends,
        acceptance_criteria=acceptance_criteria,
    )
    session.add(task)
    session.flush()
    return task


def list_tasks(session: Session, status: str | None, limit: int | None = None) -> list[Task]:
    statement = select(Task).order_by(Task.created_at.desc(), Task.id.desc())
    if status and status != "all":
        statement = statement.where(Task.status == status)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def add_snapshot(
    session: Session,
    snapshot_type: str,
    title: str | None,
    content: str,
    tags: dict | list | None,
    task_id: int | None = None,
) -> ContextSnapshot:
    snapshot = ContextSnapshot(
        task_id=task_id,
        snapshot_type=snapshot_type,
        title=title,
        content=content,
        tags=tags,
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def list_snapshots(session: Session, limit: int | None = None, task_id: int | None = None) -> list[ContextSnapshot]:
    statement = select(ContextSnapshot).order_by(ContextSnapshot.created_at.desc(), ContextSnapshot.id.desc())
    if task_id is not None:
        statement = statement.where(ContextSnapshot.task_id == task_id)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def update_task_status(session: Session, task_id: int, status: str) -> Task | None:
    task = session.get(Task, task_id)
    if task is None:
        return None
    task.status = status
    session.flush()
    return task


def list_task_children(session: Session, parent_task_id: int, limit: int | None = None) -> list[Task]:
    statement = select(Task).where(Task.parent_task_id == parent_task_id).order_by(Task.sort_order.asc(), Task.id.asc())
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def list_task_tree(session: Session, root_task_id: int) -> dict[str, object] | None:
    root = session.get(Task, root_task_id)
    if root is None:
        return None
    children = list_task_children(session, root_task_id, limit=None)
    return {"task": root, "children": children}


def update_task_fields(session: Session, task_id: int, **fields) -> Task | None:
    task = session.get(Task, task_id)
    if task is None:
        return None
    if "task_kind" in fields and fields["task_kind"] is not None:
        _validate_task_kind(str(fields["task_kind"]))
    if "sort_order" in fields and fields["sort_order"] is not None:
        _validate_sort_order(int(fields["sort_order"]))
    if "parent_task_id" in fields and fields["parent_task_id"] is not None:
        parent_task_id = int(fields["parent_task_id"])
        if parent_task_id == task_id:
            raise ValueError("A task cannot be parent of itself.")
        _validate_parent_task(session, parent_task_id)
    if "depends_on" in fields and fields["depends_on"] is not None:
        fields["depends_on"] = _serialize_depends_on(fields["depends_on"], current_task_id=task_id)
    for key, value in fields.items():
        if hasattr(task, key) and value is not None:
            setattr(task, key, value)
    session.flush()
    return task


def reorder_task(session: Session, task_id: int, sort_order: int) -> Task | None:
    return update_task_fields(session, task_id, sort_order=sort_order)


def recompute_parent_status(session: Session, parent_task_id: int) -> Task | None:
    parent = session.get(Task, parent_task_id)
    if parent is None:
        return None
    children = list_task_children(session, parent_task_id, limit=None)
    if not children:
        return parent
    statuses = [str(child.status or "pending") for child in children]
    if all(status == "done" for status in statuses):
        parent.status = "done"
    elif any(status == "blocked" for status in statuses):
        parent.status = "blocked"
    elif any(status == "in_progress" for status in statuses):
        parent.status = "in_progress"
    elif all(status == "pending" for status in statuses):
        parent.status = "pending"
    else:
        parent.status = "in_progress"
    session.flush()
    return parent


def _validate_task_kind(task_kind: str) -> None:
    if task_kind not in {"task", "plan", "subtask"}:
        raise ValueError("task_kind must be one of: task, plan, subtask")


def _validate_sort_order(sort_order: int) -> None:
    if not isinstance(sort_order, int):
        raise ValueError("sort_order must be an integer")


def _validate_parent_task(session: Session, parent_task_id: int | None) -> None:
    if parent_task_id is None:
        return
    parent = session.get(Task, int(parent_task_id))
    if parent is None:
        raise ValueError(f"parent_task_id does not exist: {parent_task_id}")


def _serialize_depends_on(depends_on: list[int] | None, current_task_id: int | None = None) -> str | None:
    if depends_on is None:
        return None
    normalized = [int(item) for item in depends_on]
    if current_task_id is not None and current_task_id in normalized:
        raise ValueError("A task cannot depend on itself.")
    return json.dumps(normalized)


def create_task_log(
    session: Session,
    task_id: int,
    content: str,
    agent_name: str | None = None,
    log_type: str = "summary",
) -> TaskLog:
    task_log = TaskLog(
        task_id=task_id,
        content=content,
        agent_name=agent_name,
        log_type=log_type,
    )
    session.add(task_log)
    session.flush()
    return task_log


def list_task_logs(
    session: Session,
    task_id: int | None = None,
    agent_name: str | None = None,
    log_type: str | None = None,
    limit: int = 20,
) -> list[TaskLog]:
    statement = select(TaskLog).order_by(TaskLog.created_at.desc(), TaskLog.id.desc()).limit(limit)
    if task_id is not None:
        statement = statement.where(TaskLog.task_id == task_id)
    if agent_name:
        statement = statement.where(TaskLog.agent_name == agent_name)
    if log_type:
        statement = statement.where(TaskLog.log_type == log_type)
    return list(session.scalars(statement))


def upsert_orchestration_execution(
    session: Session,
    execution_id: str,
    title: str,
    description: str | None,
    assigned_agent: str | None,
    root_task_id: str,
    status: str = "pending",
    summary: str | None = None,
) -> dict[str, object]:
    execution = session.get(OrchestrationExecution, execution_id)
    if execution is None:
        execution = OrchestrationExecution(
            execution_id=execution_id,
            title=title,
            description=description,
            assigned_agent=assigned_agent,
            root_task_id=root_task_id,
            status=status,
            summary=summary,
        )
        session.add(execution)
    else:
        execution.title = title
        execution.description = description
        execution.assigned_agent = assigned_agent
        execution.root_task_id = root_task_id
        execution.status = status
        execution.summary = summary
    session.flush()
    return _execution_to_dict(execution)


def list_orchestration_executions(session: Session, limit: int | None = None) -> list[dict[str, object]]:
    statement = select(OrchestrationExecution).order_by(OrchestrationExecution.created_at.desc(), OrchestrationExecution.execution_id.desc())
    if limit is not None:
        statement = statement.limit(limit)
    return [_execution_to_dict(row) for row in session.scalars(statement)]


def get_orchestration_execution(session: Session, execution_id: str) -> dict[str, object] | None:
    execution = session.get(OrchestrationExecution, execution_id)
    return _execution_to_dict(execution) if execution is not None else None


def upsert_orchestration_task(
    session: Session,
    task_id: str,
    execution_id: str,
    parent_id: str | None,
    dependencies: list[str],
    files: list[str],
    validation_command: str | None,
    status: str,
) -> dict[str, object]:
    task = session.get(OrchestrationTask, task_id)
    if task is None:
        task = OrchestrationTask(
            task_id=task_id,
            execution_id=execution_id,
            parent_id=parent_id,
            dependencies=dependencies,
            files=files,
            validation_command=validation_command,
            status=status,
        )
        session.add(task)
    else:
        task.execution_id = execution_id
        task.parent_id = parent_id
        task.dependencies = dependencies
        task.files = files
        task.validation_command = validation_command
        task.status = status
    session.flush()
    return _orchestration_task_to_dict(task)


def get_orchestration_task(session: Session, task_id: str) -> dict[str, object] | None:
    task = session.get(OrchestrationTask, task_id)
    return _orchestration_task_to_dict(task) if task is not None else None


def list_orchestration_tasks(session: Session, execution_id: str | None = None) -> list[dict[str, object]]:
    statement = select(OrchestrationTask).order_by(OrchestrationTask.created_at.asc(), OrchestrationTask.task_id.asc())
    if execution_id is not None:
        statement = statement.where(OrchestrationTask.execution_id == execution_id)
    return [_orchestration_task_to_dict(row) for row in session.scalars(statement)]


def upsert_orchestration_validation(
    session: Session,
    task_id: str,
    command: str,
    success: bool,
    output: str = "",
) -> dict[str, object]:
    validation = session.get(OrchestrationValidation, task_id)
    if validation is None:
        validation = OrchestrationValidation(task_id=task_id, command=command, success=success, output=output)
        session.add(validation)
    else:
        validation.command = command
        validation.success = success
        validation.output = output
    session.flush()
    return _orchestration_validation_to_dict(validation)


def get_orchestration_validation(session: Session, task_id: str) -> dict[str, object] | None:
    validation = session.get(OrchestrationValidation, task_id)
    return _orchestration_validation_to_dict(validation) if validation is not None else None


def replace_orchestration_conflicts(
    session: Session,
    execution_id: str | None,
    conflicts: list[dict[str, object]],
) -> list[dict[str, object]]:
    if execution_id is not None:
        session.execute(delete(OrchestrationConflict).where(OrchestrationConflict.execution_id == execution_id))
    rows: list[dict[str, object]] = []
    for conflict in conflicts:
        row = OrchestrationConflict(
            execution_id=execution_id,
            kind=str(conflict["kind"]),
            task_ids=list(conflict.get("task_ids") or ()),
            detail=str(conflict.get("detail") or ""),
        )
        session.add(row)
        session.flush()
        rows.append(_orchestration_conflict_to_dict(row))
    return rows


def add_decision(
    session: Session,
    decision_key: str,
    title: str,
    rationale: str,
    consequences: str,
    task_id: int | None = None,
) -> ArchitecturalDecision:
    decision = ArchitecturalDecision(
        task_id=task_id,
        decision_key=decision_key,
        title=title,
        rationale=rationale,
        consequences=consequences,
    )
    session.add(decision)
    session.flush()
    return decision


def list_decisions(
    session: Session,
    status: str | None = None,
    limit: int | None = None,
    task_id: int | None = None,
) -> list[ArchitecturalDecision]:
    statement = select(ArchitecturalDecision).order_by(ArchitecturalDecision.created_at.desc(), ArchitecturalDecision.id.desc())
    if status:
        statement = statement.where(ArchitecturalDecision.status == status)
    if task_id is not None:
        statement = statement.where(ArchitecturalDecision.task_id == task_id)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def _execution_to_dict(row: OrchestrationExecution) -> dict[str, object]:
    return {
        "execution_id": row.execution_id,
        "title": row.title,
        "description": row.description,
        "assigned_agent": row.assigned_agent,
        "root_task_id": row.root_task_id,
        "status": row.status or "pending",
        "summary": row.summary,
        "created_at": str(row.created_at) if row.created_at is not None else "",
        "updated_at": str(row.updated_at) if row.updated_at is not None else "",
    }


def _orchestration_task_to_dict(row: OrchestrationTask) -> dict[str, object]:
    return {
        "task_id": row.task_id,
        "execution_id": row.execution_id,
        "parent_id": row.parent_id,
        "dependencies": list(row.dependencies or []),
        "files": list(row.files or []),
        "validation_command": row.validation_command,
        "status": row.status or "pending",
        "created_at": str(row.created_at) if row.created_at is not None else "",
    }


def _orchestration_validation_to_dict(row: OrchestrationValidation) -> dict[str, object]:
    return {
        "task_id": row.task_id,
        "command": row.command,
        "success": bool(row.success),
        "output": row.output or "",
        "created_at": str(row.created_at) if row.created_at is not None else "",
    }


def _orchestration_conflict_to_dict(row: OrchestrationConflict) -> dict[str, object]:
    return {
        "id": row.id,
        "execution_id": row.execution_id,
        "kind": row.kind,
        "task_ids": list(row.task_ids or []),
        "detail": row.detail or "",
        "created_at": str(row.created_at) if row.created_at is not None else "",
    }


def supersede_decision(session: Session, old_id: int, new_id: int) -> ArchitecturalDecision | None:
    old_decision = session.get(ArchitecturalDecision, old_id)
    new_decision = session.get(ArchitecturalDecision, new_id)
    if old_decision is None or new_decision is None:
        return None
    old_decision.status = "superseded"
    old_decision.consequences = (
        f"{old_decision.consequences or ''}\nSuperseded by decision #{new_id}."
    ).strip()
    session.flush()
    return old_decision


def add_command_log(
    session: Session,
    agent_name: str,
    shell_type: str,
    command_text: str,
    success_flag: bool,
    error_message: str | None,
    correction_applied: str | None,
    task_id: int | None = None,
) -> CommandHistory:
    command = CommandHistory(
        task_id=task_id,
        agent_name=agent_name,
        shell_type=shell_type,
        command_text=command_text,
        success_flag=success_flag,
        error_message=error_message,
        correction_applied=correction_applied,
    )
    session.add(command)
    session.flush()
    return command


def list_command_history(
    session: Session,
    limit: int = 20,
    success_flag: bool | None = None,
    task_id: int | None = None,
) -> list[CommandHistory]:
    statement = select(CommandHistory).order_by(CommandHistory.created_at.desc(), CommandHistory.id.desc())
    if success_flag is not None:
        statement = statement.where(CommandHistory.success_flag == success_flag)
    if task_id is not None:
        statement = statement.where(CommandHistory.task_id == task_id)
    statement = statement.limit(limit)
    return list(session.scalars(statement))


def add_lesson(
    session: Session,
    category: str,
    problem_description: str,
    solution_description: str,
    prevention_strategy: str,
    task_id: int | None = None,
) -> LessonLearned:
    lesson = LessonLearned(
        task_id=task_id,
        category=category,
        problem_description=problem_description,
        solution_description=solution_description,
        prevention_strategy=prevention_strategy,
    )
    session.add(lesson)
    session.flush()
    return lesson


def list_lessons(
    session: Session,
    category: str | None = None,
    limit: int | None = None,
    task_id: int | None = None,
) -> list[LessonLearned]:
    statement = select(LessonLearned).order_by(LessonLearned.created_at.desc(), LessonLearned.id.desc())
    if category:
        statement = statement.where(LessonLearned.category == category)
    if task_id is not None:
        statement = statement.where(LessonLearned.task_id == task_id)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))
