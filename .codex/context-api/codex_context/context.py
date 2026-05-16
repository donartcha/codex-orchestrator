from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .backends import BackendStatus, ContextBackend, MariaDBBackend
from .fallback import select_backend
from .models import ArchitecturalDecision, CommandHistory, LessonLearned, Task, TaskLog


class CodexContext:
    """Small facade for reading and writing persistent Codex context."""

    def __init__(self, backend: ContextBackend | None = None, engine: Engine | None = None) -> None:
        if backend is not None and engine is not None:
            raise ValueError("Pass either backend or engine, not both.")
        if backend is not None:
            self.backend = backend
            self._backend_attempts = [backend.status]
        elif engine is not None:
            self.backend = MariaDBBackend(engine=engine)
            self._backend_attempts = [self.backend.status]
        else:
            selection = select_backend()
            self.backend = selection.backend
            self._backend_attempts = selection.attempts
        self.engine = getattr(self.backend, "engine", None)

    def close(self) -> None:
        self.backend.close()

    def backend_status(self) -> BackendStatus:
        return self.backend.status

    def backend_attempts(self) -> list[BackendStatus]:
        return list(self._backend_attempts)

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self.backend.session() as session:
            yield session

    def remember_task(
        self,
        title: str,
        description: str,
        assigned_agent: str | None = None,
        priority: str = "normal",
    ) -> Task:
        return self.backend.remember_task(title, description, assigned_agent, priority)

    def tasks(self, status: str = "pending", limit: int | None = None) -> list[Task]:
        return self.backend.tasks(status, limit)

    def set_task_status(self, task_id: int, status: str) -> Task | None:
        return self.backend.set_task_status(task_id, status)

    def remember_task_log(
        self,
        task_id: int,
        content: str,
        agent_name: str | None = None,
        log_type: str = "summary",
    ) -> TaskLog:
        return self.backend.remember_task_log(task_id, content, agent_name, log_type)

    def task_logs(
        self,
        task_id: int | None = None,
        agent_name: str | None = None,
        log_type: str | None = None,
        limit: int = 20,
    ) -> list[TaskLog]:
        return self.backend.task_logs(task_id, agent_name, log_type, limit)

    def remember_decision(
        self,
        decision_key: str,
        title: str,
        rationale: str,
        consequences: str,
    ) -> ArchitecturalDecision:
        return self.backend.remember_decision(decision_key, title, rationale, consequences)

    def decisions(
        self,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[ArchitecturalDecision]:
        return self.backend.decisions(status, limit)

    def remember_command(
        self,
        agent_name: str,
        shell_type: str,
        command_text: str,
        success_flag: bool,
        error_message: str | None = None,
        correction_applied: str | None = None,
    ) -> CommandHistory:
        return self.backend.remember_command(
            agent_name,
            shell_type,
            command_text,
            success_flag,
            error_message,
            correction_applied,
        )

    def commands(self, limit: int = 20, success_flag: bool | None = None) -> list[CommandHistory]:
        return self.backend.commands(limit, success_flag)

    def remember_lesson(
        self,
        category: str,
        problem_description: str,
        solution_description: str,
        prevention_strategy: str,
    ) -> LessonLearned:
        return self.backend.remember_lesson(
            category,
            problem_description,
            solution_description,
            prevention_strategy,
        )

    def lessons(self, category: str | None = None, limit: int | None = None) -> list[LessonLearned]:
        return self.backend.lessons(category, limit)

    def remember_recovery_lesson(
        self,
        category: str,
        problem_description: str,
        solution_description: str,
        prevention_strategy: str,
    ) -> LessonLearned | None:
        """Record a reusable lesson if an equivalent recent lesson is absent."""
        existing_lessons = self.lessons(category=category, limit=50)
        for lesson in existing_lessons:
            if (
                lesson.problem_description == problem_description
                and lesson.solution_description == solution_description
            ):
                return None
        return self.remember_lesson(
            category=category,
            problem_description=problem_description,
            solution_description=solution_description,
            prevention_strategy=prevention_strategy,
        )

    def failed_commands(self, limit: int = 20) -> list[CommandHistory]:
        return self.commands(limit=limit, success_flag=False)

    def remember_fallback_event(
        self,
        agent_name: str,
        shell_type: str,
        command_text: str,
        fallback_from: str,
        fallback_to: str,
        reason: str,
    ) -> CommandHistory:
        correction = f"Fallback from {fallback_from} to {fallback_to}: {reason}"
        return self.remember_command(
            agent_name=agent_name,
            shell_type=shell_type,
            command_text=command_text,
            success_flag=True,
            correction_applied=correction,
        )


@contextmanager
def open_context() -> Iterator[CodexContext]:
    context = CodexContext()
    try:
        yield context
    finally:
        context.close()
