from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import ArchitecturalDecision, CommandHistory, ContextSnapshot, LessonLearned, Task, TaskLog
from .base import BackendStatus

CONTEXT_API_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = CONTEXT_API_ROOT.parents[1]
DEFAULT_FILE_PATH = WORKSPACE_ROOT / ".codex" / "context" / "memory-fallback.json"

COLLECTIONS = {
    "snapshots": ContextSnapshot,
    "tasks": Task,
    "task_logs": TaskLog,
    "decisions": ArchitecturalDecision,
    "commands": CommandHistory,
    "lessons": LessonLearned,
}


class FileBackend:
    name = "file"

    def __init__(self, path: str | Path | None = None, warning: str | None = None) -> None:
        self.path = Path(path or os.environ.get("CODEX_CONTEXT_FILE_PATH") or DEFAULT_FILE_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(self._empty_store())
        self._read()
        self.status = BackendStatus(
            name=self.name,
            active=True,
            degraded=True,
            warning=warning,
            details={"path": str(self.path)},
        )

    def close(self) -> None:
        return None

    @contextmanager
    def session(self) -> Iterator[Session]:
        raise RuntimeError("Direct SQLAlchemy sessions are unavailable on the file fallback backend.")
        yield  # pragma: no cover

    def remember_task(self, title, description, assigned_agent=None, priority="normal"):
        return self._append(
            "tasks",
            {
                "title": title,
                "description": description,
                "assigned_agent": assigned_agent,
                "priority": priority,
                "status": "pending",
            },
        )

    def tasks(self, status="pending", limit=None):
        rows = [row for row in self._objects("tasks") if row.status == status]
        return self._limit(rows, limit)

    def set_task_status(self, task_id, status):
        store = self._read()
        for row in store["tasks"]:
            if int(row["id"]) == int(task_id):
                row["status"] = status
                row["updated_at"] = self._now()
                self._write(store)
                return self._object("tasks", row)
        return None

    def remember_snapshot(self, snapshot_type, title=None, content="", tags=None):
        return self._append(
            "snapshots",
            {
                "snapshot_type": snapshot_type,
                "title": title,
                "content": content,
                "tags": tags,
            },
        )

    def snapshots(self, limit=None):
        return self._limit(self._objects("snapshots"), limit)

    def remember_task_log(self, task_id, content, agent_name=None, log_type="summary"):
        return self._append(
            "task_logs",
            {
                "task_id": task_id,
                "content": content,
                "agent_name": agent_name,
                "log_type": log_type,
            },
        )

    def task_logs(self, task_id=None, agent_name=None, log_type=None, limit=20):
        rows = self._objects("task_logs")
        if task_id is not None:
            rows = [row for row in rows if int(row.task_id) == int(task_id)]
        if agent_name:
            rows = [row for row in rows if row.agent_name == agent_name]
        if log_type:
            rows = [row for row in rows if row.log_type == log_type]
        return self._limit(rows, limit)

    def remember_decision(self, decision_key, title, rationale, consequences):
        return self._append(
            "decisions",
            {
                "decision_key": decision_key,
                "title": title,
                "rationale": rationale,
                "consequences": consequences,
                "status": "active",
            },
        )

    def decisions(self, status=None, limit=None):
        rows = self._objects("decisions")
        if status:
            rows = [row for row in rows if row.status == status]
        return self._limit(rows, limit)

    def supersede_decision(self, old_id, new_id):
        store = self._read()
        new_exists = any(int(row["id"]) == int(new_id) for row in store["decisions"])
        if not new_exists:
            return None
        for row in store["decisions"]:
            if int(row["id"]) == int(old_id):
                row["status"] = "superseded"
                consequence = str(row.get("consequences") or "").strip()
                row["consequences"] = f"{consequence}\nSuperseded by decision #{new_id}.".strip()
                row["updated_at"] = self._now()
                self._write(store)
                return self._object("decisions", row)
        return None

    def remember_command(self, agent_name, shell_type, command_text, success_flag, error_message=None, correction_applied=None):
        return self._append(
            "commands",
            {
                "agent_name": agent_name,
                "shell_type": shell_type,
                "command_text": command_text,
                "success_flag": bool(success_flag),
                "error_message": error_message,
                "correction_applied": correction_applied,
            },
        )

    def commands(self, limit=20, success_flag=None):
        rows = self._objects("commands")
        if success_flag is not None:
            rows = [row for row in rows if bool(row.success_flag) == bool(success_flag)]
        return self._limit(rows, limit)

    def remember_lesson(self, category, problem_description, solution_description, prevention_strategy):
        return self._append(
            "lessons",
            {
                "category": category,
                "problem_description": problem_description,
                "solution_description": solution_description,
                "prevention_strategy": prevention_strategy,
            },
        )

    def lessons(self, category=None, limit=None):
        rows = self._objects("lessons")
        if category:
            rows = [row for row in rows if row.category == category]
        return self._limit(rows, limit)

    def _empty_store(self) -> dict[str, list[dict[str, object]]]:
        return {name: [] for name in COLLECTIONS}

    def _read(self) -> dict[str, list[dict[str, object]]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = self._empty_store()
        for name in COLLECTIONS:
            data.setdefault(name, [])
        return data

    def _write(self, data: dict[str, list[dict[str, object]]]) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _append(self, collection: str, values: dict[str, object]):
        store = self._read()
        rows = store[collection]
        next_id = max([int(row.get("id", 0)) for row in rows] or [0]) + 1
        now = self._now()
        row = {"id": next_id, "created_at": now, **values}
        if collection in {"snapshots", "tasks", "decisions"}:
            row.setdefault("updated_at", now)
        rows.append(row)
        self._write(store)
        return self._object(collection, row)

    def _objects(self, collection: str):
        rows = self._read()[collection]
        return [self._object(collection, row) for row in reversed(rows)]

    def _object(self, collection: str, row: dict[str, object]):
        model = COLLECTIONS[collection]
        return model(**row)

    def _limit(self, rows, limit):
        return rows if limit is None else rows[:limit]

    def _now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
