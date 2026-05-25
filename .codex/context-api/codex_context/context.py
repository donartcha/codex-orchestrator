from __future__ import annotations

import ast
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .backends import BackendStatus, ContextBackend, MariaDBBackend
from .fallback import select_backend
from .memory_lifecycle import compact_memory, detect_contradictions, serialize_memory_state
from .models import ArchitecturalDecision, CommandHistory, LessonLearned, Task, TaskLog
from .lesson_taxonomy import suggest_categories
from .sanitizer import SanitizationReport, sanitize_memory

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session

__all__ = [
    "CodexContext",
    "FacadeUsageViolation",
    "FacadeUsageReport",
    "SanitizationReport",
    "get_context_config",
    "open_context",
    "validate_facade_usage",
]


_PUBLIC_API = tuple(__all__)
_DEPRECATED_EXPORTS = {"Engine", "Session", "engine"}
_BYPASS_MODULES = {
    "codex_context.backends",
    "codex_context.db",
    "codex_context.repositories",
}


@dataclass(frozen=True)
class FacadeUsageViolation:
    path: str
    line: int
    name: str
    reason: str


@dataclass(frozen=True)
class FacadeUsageReport:
    root: str
    violations: tuple[FacadeUsageViolation, ...]

    @property
    def ok(self) -> bool:
        return not self.violations


class CodexContext:
    """Small facade for reading and writing persistent Codex context."""

    def __init__(self, backend: ContextBackend | None = None, engine: "Engine | None" = None) -> None:
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
        self._engine = getattr(self.backend, "engine", None)

    def close(self) -> None:
        self.backend.close()

    @property
    def engine(self) -> Any:
        warnings.warn(
            "CodexContext.engine is deprecated; use facade methods or backend_status() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._engine

    def backend_status(self) -> BackendStatus:
        return self.backend.status

    def backend_attempts(self) -> list[BackendStatus]:
        return list(self._backend_attempts)

    @contextmanager
    def session(self) -> Iterator["Session"]:
        warnings.warn(
            "CodexContext.session() is deprecated; use CodexContext facade methods instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        with self.backend.session() as session:
            yield session

    def remember_task(
        self,
        title: str,
        description: str,
        assigned_agent: str | None = None,
        priority: str = "normal",
        parent_task_id: int | None = None,
        task_kind: str = "task",
        sort_order: int = 0,
        depends_on: list[int] | None = None,
        acceptance_criteria: str | None = None,
    ) -> Task:
        payload = self._sanitize_write(
            {
                "title": title,
                "description": description,
                "assigned_agent": assigned_agent,
                "priority": priority,
                "parent_task_id": parent_task_id,
                "task_kind": task_kind,
                "sort_order": sort_order,
                "depends_on": depends_on,
                "acceptance_criteria": acceptance_criteria,
            }
        )
        return self.backend.remember_task(
            payload["title"],
            payload["description"],
            payload["assigned_agent"],
            payload["priority"],
            payload["parent_task_id"],
            payload["task_kind"],
            payload["sort_order"],
            payload["depends_on"],
            payload["acceptance_criteria"],
        )

    def tasks(self, status: str | None = "pending", limit: int | None = None) -> list[Task]:
        return self.backend.tasks(status, limit)
    def task_children(self, parent_task_id: int, limit: int | None = None) -> list[Task]:
        return self.backend.task_children(parent_task_id, limit)
    def task_tree(self, root_task_id: int) -> dict[str, object] | None:
        return self.backend.task_tree(root_task_id)
    def update_task(self, task_id: int, **fields: Any) -> Task | None:
        return self.backend.update_task(task_id, **fields)
    def reorder_task(self, task_id: int, sort_order: int) -> Task | None:
        return self.backend.reorder_task(task_id, sort_order)
    def recompute_parent_status(self, parent_task_id: int) -> Task | None:
        return self.backend.recompute_parent_status(parent_task_id)

    def set_task_status(self, task_id: int, status: str) -> Task | None:
        return self.backend.set_task_status(task_id, status)

    def remember_snapshot(
        self,
        snapshot_type: str = "manual",
        title: str | None = None,
        limit: int = 100,
        tags: dict | list | None = None,
        task_id: int | None = None,
    ):
        content = serialize_memory_state(self, limit=limit)
        payload = self._sanitize_write(
            {
                "task_id": task_id,
                "snapshot_type": snapshot_type,
                "title": title,
                "content": content,
                "tags": tags,
            }
        )
        return self.backend.remember_snapshot(
            payload["snapshot_type"],
            payload["title"],
            payload["content"],
            payload["tags"],
            payload["task_id"],
        )

    def snapshots(self, limit: int | None = None, task_id: int | None = None):
        return self.backend.snapshots(limit, task_id)

    def remember_task_log(
        self,
        task_id: int,
        content: str,
        agent_name: str | None = None,
        log_type: str = "summary",
    ) -> TaskLog:
        payload = self._sanitize_write(
            {
                "content": content,
                "agent_name": agent_name,
                "log_type": log_type,
            }
        )
        return self.backend.remember_task_log(task_id, payload["content"], payload["agent_name"], payload["log_type"])

    def task_logs(
        self,
        task_id: int | None = None,
        agent_name: str | None = None,
        log_type: str | None = None,
        limit: int = 20,
    ) -> list[TaskLog]:
        return self.backend.task_logs(task_id, agent_name, log_type, limit)

    def remember_orchestration_execution(
        self,
        execution_id: str,
        title: str,
        description: str | None,
        assigned_agent: str | None,
        root_task_id: str,
        status: str = "pending",
        summary: str | None = None,
    ) -> dict[str, object]:
        payload = self._sanitize_write(
            {
                "execution_id": execution_id,
                "title": title,
                "description": description,
                "assigned_agent": assigned_agent,
                "root_task_id": root_task_id,
                "status": status,
                "summary": summary,
            }
        )
        return self.backend.remember_orchestration_execution(
            str(payload["execution_id"]),
            str(payload["title"]),
            payload["description"],
            payload["assigned_agent"],
            str(payload["root_task_id"]),
            str(payload["status"]),
            payload["summary"],
        )

    def orchestration_executions(self, limit: int | None = None) -> list[dict[str, object]]:
        return self.backend.orchestration_executions(limit)

    def orchestration_execution(self, execution_id: str) -> dict[str, object] | None:
        return self.backend.orchestration_execution(execution_id)

    def remember_orchestration_task(
        self,
        task_id: str,
        execution_id: str,
        parent_id: str | None = None,
        dependencies: tuple[str, ...] = (),
        files: tuple[str, ...] = (),
        validation_command: str | None = None,
        status: str = "pending",
    ) -> dict[str, object]:
        payload = self._sanitize_write(
            {
                "task_id": task_id,
                "execution_id": execution_id,
                "parent_id": parent_id,
                "dependencies": list(dependencies),
                "files": list(files),
                "validation_command": validation_command,
                "status": status,
            }
        )
        return self.backend.remember_orchestration_task(
            str(payload["task_id"]),
            str(payload["execution_id"]),
            payload["parent_id"],
            list(payload["dependencies"]),
            list(payload["files"]),
            payload["validation_command"],
            str(payload["status"]),
        )

    def orchestration_task(self, task_id: str) -> dict[str, object] | None:
        return self.backend.orchestration_task(task_id)

    def orchestration_tasks(self, execution_id: str | None = None) -> list[dict[str, object]]:
        return self.backend.orchestration_tasks(execution_id)

    def remember_orchestration_validation(
        self,
        task_id: str,
        command: str,
        success: bool,
        output: str = "",
    ) -> dict[str, object]:
        payload = self._sanitize_write(
            {
                "task_id": task_id,
                "command": command,
                "output": output,
            }
        )
        return self.backend.remember_orchestration_validation(
            str(payload["task_id"]),
            str(payload["command"]),
            bool(success),
            str(payload["output"]),
        )

    def orchestration_validation(self, task_id: str) -> dict[str, object] | None:
        return self.backend.orchestration_validation(task_id)

    def replace_orchestration_conflicts(
        self,
        execution_id: str | None,
        conflicts: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        payload = self._sanitize_write({"execution_id": execution_id, "conflicts": conflicts})
        return self.backend.replace_orchestration_conflicts(
            payload["execution_id"],
            list(payload["conflicts"]),
        )

    def remember_decision(
        self,
        decision_key: str,
        title: str,
        rationale: str,
        consequences: str,
        task_id: int | None = None,
    ) -> ArchitecturalDecision:
        payload = self._sanitize_write(
            {
                "task_id": task_id,
                "decision_key": decision_key,
                "title": title,
                "rationale": rationale,
                "consequences": consequences,
            }
        )
        return self.backend.remember_decision(
            payload["decision_key"],
            payload["title"],
            payload["rationale"],
            payload["consequences"],
            payload["task_id"],
        )

    def decisions(
        self,
        status: str | None = None,
        limit: int | None = None,
        task_id: int | None = None,
    ) -> list[ArchitecturalDecision]:
        return self.backend.decisions(status, limit, task_id)

    def supersede_decision(self, old_id: int, new_id: int) -> ArchitecturalDecision | None:
        return self.backend.supersede_decision(old_id, new_id)

    def contradictions(self) -> list[object]:
        return detect_contradictions(self.decisions(limit=200))

    def compact_memory(self) -> object:
        return compact_memory(self.decisions(limit=500))

    def remember_command(
        self,
        agent_name: str,
        shell_type: str,
        command_text: str,
        success_flag: bool,
        error_message: str | None = None,
        correction_applied: str | None = None,
        task_id: int | None = None,
    ) -> CommandHistory:
        payload = self._sanitize_write(
            {
                "task_id": task_id,
                "agent_name": agent_name,
                "shell_type": shell_type,
                "command_text": command_text,
                "error_message": error_message,
                "correction_applied": correction_applied,
            }
        )
        return self.backend.remember_command(
            payload["agent_name"],
            payload["shell_type"],
            payload["command_text"],
            success_flag,
            payload["error_message"],
            payload["correction_applied"],
            payload["task_id"],
        )

    def commands(
        self,
        limit: int = 20,
        success_flag: bool | None = None,
        task_id: int | None = None,
    ) -> list[CommandHistory]:
        return self.backend.commands(limit, success_flag, task_id)

    def remember_lesson(
        self,
        category: str,
        problem_description: str,
        solution_description: str,
        prevention_strategy: str,
        task_id: int | None = None,
        create_category: bool = False,
    ) -> LessonLearned:
        if create_category:
            try:
                self.backend.remember_lesson_category(category, category.replace("-", " ").title())
            except ValueError:
                pass
        payload = self._sanitize_write(
            {
                "task_id": task_id,
                "category": category,
                "problem_description": problem_description,
                "solution_description": solution_description,
                "prevention_strategy": prevention_strategy,
            }
        )
        return self.backend.remember_lesson(
            payload["category"],
            payload["problem_description"],
            payload["solution_description"],
            payload["prevention_strategy"],
            payload["task_id"],
        )

    def lessons(
        self,
        category: str | None = None,
        limit: int | None = None,
        task_id: int | None = None,
    ) -> list[LessonLearned]:
        return self.backend.lessons(category, limit, task_id)
    def remember_lesson_category(self, key_name: str, title: str, description: str | None = None, parent_key: str | None = None):
        return self.backend.remember_lesson_category(key_name, title, description, parent_key)
    def lesson_categories(self, status: str | None = "active", limit: int | None = 100):
        return self.backend.lesson_categories(status, limit)
    def find_lesson_categories(self, query: str, limit: int = 10):
        return self.backend.find_lesson_categories(query, limit)
    def suggest_lesson_category(self, problem: str, solution: str | None = None, limit: int = 5):
        source = f"{problem} {solution or ''}".strip()
        return suggest_categories(source, limit=limit)

    def remember_recovery_lesson(
        self,
        category: str,
        problem_description: str,
        solution_description: str,
        prevention_strategy: str,
        task_id: int | None = None,
    ) -> LessonLearned | None:
        """Record a reusable lesson if an equivalent recent lesson is absent."""
        existing_lessons = self.lessons(category=category, limit=50, task_id=task_id)
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
            task_id=task_id,
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

    def _sanitize_write(self, payload: dict[str, object]) -> dict[str, object]:
        sanitized, _report = sanitize_memory(payload, repo_root=Path(__file__).resolve().parents[2])
        return sanitized


@contextmanager
def open_context(backend: ContextBackend | None = None) -> Iterator[CodexContext]:
    context = CodexContext(backend=backend)
    try:
        yield context
    finally:
        context.close()


def get_context_config() -> dict[str, object]:
    """Return public facade metadata without exposing backend internals."""
    return {
        "public_api": list(_PUBLIC_API),
        "deprecated_exports": sorted(_DEPRECATED_EXPORTS),
    }


def validate_facade_usage(root: str | Path | None = None) -> FacadeUsageReport:
    """Scan project Python files for imports that bypass the public context facade."""
    root_path = Path(root or Path(__file__).resolve().parents[1])
    violations: list[FacadeUsageViolation] = []
    for path in _iter_project_python_files(root_path):
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            violations.append(FacadeUsageViolation(str(path), 0, path.name, f"Could not inspect file: {exc}"))
            continue
        violations.extend(_context_import_violations(path, tree))
    return FacadeUsageReport(str(root_path), tuple(violations))


def _iter_project_python_files(root_path: Path) -> Iterator[Path]:
    skipped = {".git", ".pytest_cache", ".venv", "__pycache__"}
    for path in root_path.rglob("*.py"):
        if any(part in skipped for part in path.parts):
            continue
        yield path


def _context_import_violations(path: Path, tree: ast.AST) -> list[FacadeUsageViolation]:
    violations: list[FacadeUsageViolation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "codex_context.context":
            for alias in node.names:
                if alias.name not in _PUBLIC_API:
                    violations.append(
                        FacadeUsageViolation(
                            str(path),
                            node.lineno,
                            alias.name,
                            "Import is not part of codex_context.context public facade.",
                        )
                    )
        elif isinstance(node, ast.ImportFrom) and node.module in _BYPASS_MODULES:
            if _is_internal_context_api_file(path):
                continue
            for alias in node.names:
                violations.append(
                    FacadeUsageViolation(
                        str(path),
                        node.lineno,
                        alias.name,
                        f"Import bypasses codex_context.context facade via {node.module}.",
                    )
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _BYPASS_MODULES and not _is_internal_context_api_file(path):
                    violations.append(
                        FacadeUsageViolation(
                            str(path),
                            node.lineno,
                            alias.name,
                            f"Import bypasses codex_context.context facade via {alias.name}.",
                        )
                    )
    return violations


def _is_internal_context_api_file(path: Path) -> bool:
    parts = set(path.parts)
    if "codex_context" in parts or "tests" in parts:
        return True
    return path.name == "init_db.py" and "scripts" in parts


def __getattr__(name: str) -> object:
    if name == "Engine":
        warnings.warn(
            "Importing Engine from codex_context.context is deprecated; import it from sqlalchemy.engine if needed.",
            DeprecationWarning,
            stacklevel=2,
        )
        from sqlalchemy.engine import Engine

        return Engine
    if name == "Session":
        warnings.warn(
            "Importing Session from codex_context.context is deprecated; import it from sqlalchemy.orm if needed.",
            DeprecationWarning,
            stacklevel=2,
        )
        from sqlalchemy.orm import Session

        return Session
    if name == "engine":
        warnings.warn(
            "codex_context.context.engine is deprecated and no longer a module-level public API.",
            DeprecationWarning,
            stacklevel=2,
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
