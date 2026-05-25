from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..db import create_db_engine, session_scope
from ..repositories import (
    add_command_log,
    add_decision,
    add_lesson,
    create_lesson_category,
    find_lesson_categories,
    get_lesson_category_by_key,
    add_snapshot,
    add_task,
    list_task_children,
    list_task_tree,
    reorder_task as repo_reorder_task,
    recompute_parent_status as repo_recompute_parent_status,
    update_task_fields,
    create_task_log,
    get_orchestration_execution,
    get_orchestration_task,
    get_orchestration_validation,
    list_command_history,
    list_decisions,
    list_lessons,
    list_lesson_categories,
    list_orchestration_executions,
    list_orchestration_tasks,
    list_snapshots,
    list_task_logs,
    list_tasks,
    replace_orchestration_conflicts,
    supersede_decision,
    update_task_status,
    upsert_orchestration_execution,
    upsert_orchestration_task,
    upsert_orchestration_validation,
)
from ..schema_migrations import ensure_task_scope_columns
from .base import BackendStatus


class MariaDBBackend:
    name = "mariadb"

    def __init__(self, engine: Engine | None = None) -> None:
        self._owns_engine = engine is None
        self.engine = engine or create_db_engine()
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        ensure_task_scope_columns(self.engine)
        self.status = BackendStatus(name=self.name, active=True, details={"url": self.engine.url.render_as_string(hide_password=True)})

    def close(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    @contextmanager
    def session(self) -> Iterator[Session]:
        with session_scope(self.engine) as session:
            yield session

    def remember_task(self, title, description, assigned_agent=None, priority="normal", parent_task_id=None, task_kind="task", sort_order=0, depends_on=None, acceptance_criteria=None):
        with self.session() as session:
            return add_task(session, title, description, assigned_agent, priority, parent_task_id, task_kind, sort_order, depends_on, acceptance_criteria)

    def tasks(self, status="pending", limit=None):
        with self.session() as session:
            return list_tasks(session, status, limit)
    def task_children(self, parent_task_id, limit=None):
        with self.session() as session:
            return list_task_children(session, parent_task_id, limit)
    def task_tree(self, root_task_id):
        with self.session() as session:
            return list_task_tree(session, root_task_id)
    def update_task(self, task_id, **fields):
        with self.session() as session:
            return update_task_fields(session, task_id, **fields)
    def reorder_task(self, task_id, sort_order):
        with self.session() as session:
            return repo_reorder_task(session, task_id, sort_order)
    def recompute_parent_status(self, parent_task_id):
        with self.session() as session:
            return repo_recompute_parent_status(session, parent_task_id)

    def set_task_status(self, task_id, status):
        with self.session() as session:
            return update_task_status(session, task_id, status)

    def remember_snapshot(self, snapshot_type, title=None, content="", tags=None, task_id=None):
        with self.session() as session:
            return add_snapshot(session, snapshot_type, title, content, tags, task_id)

    def snapshots(self, limit=None, task_id=None):
        with self.session() as session:
            return list_snapshots(session, limit, task_id)

    def remember_task_log(self, task_id, content, agent_name=None, log_type="summary"):
        with self.session() as session:
            return create_task_log(session, task_id, content, agent_name, log_type)

    def task_logs(self, task_id=None, agent_name=None, log_type=None, limit=20):
        with self.session() as session:
            return list_task_logs(session, task_id, agent_name, log_type, limit)

    def remember_orchestration_execution(self, execution_id, title, description, assigned_agent, root_task_id, status="pending", summary=None):
        with self.session() as session:
            return upsert_orchestration_execution(session, execution_id, title, description, assigned_agent, root_task_id, status, summary)

    def orchestration_executions(self, limit=None):
        with self.session() as session:
            return list_orchestration_executions(session, limit)

    def orchestration_execution(self, execution_id):
        with self.session() as session:
            return get_orchestration_execution(session, execution_id)

    def remember_orchestration_task(self, task_id, execution_id, parent_id=None, dependencies=None, files=None, validation_command=None, status="pending"):
        with self.session() as session:
            return upsert_orchestration_task(
                session,
                task_id,
                execution_id,
                parent_id,
                list(dependencies or []),
                list(files or []),
                validation_command,
                status,
            )

    def orchestration_task(self, task_id):
        with self.session() as session:
            return get_orchestration_task(session, task_id)

    def orchestration_tasks(self, execution_id=None):
        with self.session() as session:
            return list_orchestration_tasks(session, execution_id)

    def remember_orchestration_validation(self, task_id, command, success, output=""):
        with self.session() as session:
            return upsert_orchestration_validation(session, task_id, command, bool(success), output)

    def orchestration_validation(self, task_id):
        with self.session() as session:
            return get_orchestration_validation(session, task_id)

    def replace_orchestration_conflicts(self, execution_id, conflicts):
        with self.session() as session:
            return replace_orchestration_conflicts(session, execution_id, conflicts)

    def remember_decision(self, decision_key, title, rationale, consequences, task_id=None):
        with self.session() as session:
            return add_decision(session, decision_key, title, rationale, consequences, task_id)

    def decisions(self, status=None, limit=None, task_id=None):
        with self.session() as session:
            return list_decisions(session, status, limit, task_id)

    def supersede_decision(self, old_id, new_id):
        with self.session() as session:
            return supersede_decision(session, old_id, new_id)

    def remember_command(self, agent_name, shell_type, command_text, success_flag, error_message=None, correction_applied=None, task_id=None):
        with self.session() as session:
            return add_command_log(session, agent_name, shell_type, command_text, success_flag, error_message, correction_applied, task_id)

    def commands(self, limit=20, success_flag=None, task_id=None):
        with self.session() as session:
            return list_command_history(session, limit, success_flag, task_id)

    def remember_lesson(self, category, problem_description, solution_description, prevention_strategy, task_id=None):
        with self.session() as session:
            cat = get_lesson_category_by_key(session, category)
            if cat is None:
                raise ValueError(f"Unknown lesson category: {category}")
            return add_lesson(session, cat.key_name, problem_description, solution_description, prevention_strategy, task_id, category_id=cat.id)

    def lessons(self, category=None, limit=None, task_id=None):
        with self.session() as session:
            return list_lessons(session, category, limit, task_id)
    def remember_lesson_category(self, key_name, title, description=None, parent_key=None):
        with self.session() as session:
            parent_id = None
            if parent_key:
                parent = get_lesson_category_by_key(session, parent_key)
                parent_id = parent.id if parent else None
            return create_lesson_category(session, key_name, title, description, parent_id=parent_id)
    def lesson_categories(self, status="active", limit=100):
        with self.session() as session:
            return list_lesson_categories(session, status, limit)
    def find_lesson_categories(self, query, limit=10):
        with self.session() as session:
            return find_lesson_categories(session, query, limit)
