from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ArchitecturalDecision, CommandHistory, LessonLearned, Task, TaskLog


def add_task(
    session: Session,
    title: str,
    description: str,
    assigned_agent: str | None,
    priority: str,
) -> Task:
    task = Task(
        title=title,
        description=description,
        assigned_agent=assigned_agent,
        priority=priority,
    )
    session.add(task)
    session.flush()
    return task


def list_tasks(session: Session, status: str, limit: int | None = None) -> list[Task]:
    statement = select(Task).where(Task.status == status).order_by(Task.created_at.desc())
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
    statement = select(TaskLog).order_by(TaskLog.created_at.desc()).limit(limit)
    if task_id is not None:
        statement = statement.where(TaskLog.task_id == task_id)
    if agent_name:
        statement = statement.where(TaskLog.agent_name == agent_name)
    if log_type:
        statement = statement.where(TaskLog.log_type == log_type)
    return list(session.scalars(statement))


def add_decision(
    session: Session,
    decision_key: str,
    title: str,
    rationale: str,
    consequences: str,
) -> ArchitecturalDecision:
    decision = ArchitecturalDecision(
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
) -> list[ArchitecturalDecision]:
    statement = select(ArchitecturalDecision).order_by(ArchitecturalDecision.created_at.desc())
    if status:
        statement = statement.where(ArchitecturalDecision.status == status)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def add_command_log(
    session: Session,
    agent_name: str,
    shell_type: str,
    command_text: str,
    success_flag: bool,
    error_message: str | None,
    correction_applied: str | None,
) -> CommandHistory:
    command = CommandHistory(
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
) -> list[CommandHistory]:
    statement = select(CommandHistory).order_by(CommandHistory.created_at.desc())
    if success_flag is not None:
        statement = statement.where(CommandHistory.success_flag == success_flag)
    statement = statement.limit(limit)
    return list(session.scalars(statement))


def add_lesson(
    session: Session,
    category: str,
    problem_description: str,
    solution_description: str,
    prevention_strategy: str,
) -> LessonLearned:
    lesson = LessonLearned(
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
) -> list[LessonLearned]:
    statement = select(LessonLearned).order_by(LessonLearned.created_at.desc())
    if category:
        statement = statement.where(LessonLearned.category == category)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))
