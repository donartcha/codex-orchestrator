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
    add_snapshot,
    add_task,
    create_task_log,
    list_command_history,
    list_decisions,
    list_lessons,
    list_snapshots,
    list_task_logs,
    list_tasks,
    supersede_decision,
    update_task_status,
)
from .base import BackendStatus


class MariaDBBackend:
    name = "mariadb"

    def __init__(self, engine: Engine | None = None) -> None:
        self._owns_engine = engine is None
        self.engine = engine or create_db_engine()
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        self.status = BackendStatus(name=self.name, active=True, details={"url": self.engine.url.render_as_string(hide_password=True)})

    def close(self) -> None:
        if self._owns_engine:
            self.engine.dispose()

    @contextmanager
    def session(self) -> Iterator[Session]:
        with session_scope(self.engine) as session:
            yield session

    def remember_task(self, title, description, assigned_agent=None, priority="normal"):
        with self.session() as session:
            return add_task(session, title, description, assigned_agent, priority)

    def tasks(self, status="pending", limit=None):
        with self.session() as session:
            return list_tasks(session, status, limit)

    def set_task_status(self, task_id, status):
        with self.session() as session:
            return update_task_status(session, task_id, status)

    def remember_snapshot(self, snapshot_type, title=None, content="", tags=None):
        with self.session() as session:
            return add_snapshot(session, snapshot_type, title, content, tags)

    def snapshots(self, limit=None):
        with self.session() as session:
            return list_snapshots(session, limit)

    def remember_task_log(self, task_id, content, agent_name=None, log_type="summary"):
        with self.session() as session:
            return create_task_log(session, task_id, content, agent_name, log_type)

    def task_logs(self, task_id=None, agent_name=None, log_type=None, limit=20):
        with self.session() as session:
            return list_task_logs(session, task_id, agent_name, log_type, limit)

    def remember_decision(self, decision_key, title, rationale, consequences):
        with self.session() as session:
            return add_decision(session, decision_key, title, rationale, consequences)

    def decisions(self, status=None, limit=None):
        with self.session() as session:
            return list_decisions(session, status, limit)

    def supersede_decision(self, old_id, new_id):
        with self.session() as session:
            return supersede_decision(session, old_id, new_id)

    def remember_command(self, agent_name, shell_type, command_text, success_flag, error_message=None, correction_applied=None):
        with self.session() as session:
            return add_command_log(session, agent_name, shell_type, command_text, success_flag, error_message, correction_applied)

    def commands(self, limit=20, success_flag=None):
        with self.session() as session:
            return list_command_history(session, limit, success_flag)

    def remember_lesson(self, category, problem_description, solution_description, prevention_strategy):
        with self.session() as session:
            return add_lesson(session, category, problem_description, solution_description, prevention_strategy)

    def lessons(self, category=None, limit=None):
        with self.session() as session:
            return list_lessons(session, category, limit)
