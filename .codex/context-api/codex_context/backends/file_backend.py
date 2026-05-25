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
    "orchestration_executions": dict,
    "orchestration_tasks": dict,
    "orchestration_validations": dict,
    "orchestration_conflicts": dict,
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

    def remember_task(self, title, description, assigned_agent=None, priority="normal", parent_task_id=None, task_kind="task", sort_order=0, depends_on=None, acceptance_criteria=None):
        return self._append(
            "tasks",
            {
                "title": title,
                "description": description,
                "assigned_agent": assigned_agent,
                "priority": priority,
                "status": "pending",
                "parent_task_id": parent_task_id,
                "task_kind": task_kind,
                "sort_order": int(sort_order),
                "depends_on": json.dumps(list(depends_on or [])) if depends_on is not None else None,
                "acceptance_criteria": acceptance_criteria,
            },
        )

    def tasks(self, status="pending", limit=None):
        rows = self._objects("tasks")
        if status and status != "all":
            rows = [row for row in rows if row.status == status]
        return self._limit(rows, limit)
    def task_children(self, parent_task_id, limit=None):
        rows = [row for row in self._objects("tasks") if int(getattr(row, "parent_task_id", 0) or 0) == int(parent_task_id)]
        rows.sort(key=lambda row: (int(getattr(row, "sort_order", 0) or 0), int(getattr(row, "id", 0) or 0)))
        return self._limit(rows, limit)
    def task_tree(self, root_task_id):
        roots = [row for row in self._objects("tasks") if int(getattr(row, "id", -1)) == int(root_task_id)]
        if not roots:
            return None
        return {"task": roots[0], "children": self.task_children(root_task_id, limit=None)}
    def update_task(self, task_id, **fields):
        store = self._read()
        for row in store["tasks"]:
            if int(row["id"]) == int(task_id):
                for key, value in fields.items():
                    if value is None:
                        continue
                    if key == "depends_on":
                        row[key] = json.dumps(list(value))
                    else:
                        row[key] = value
                row["updated_at"] = self._now()
                self._write(store)
                return self._object("tasks", row)
        return None
    def reorder_task(self, task_id, sort_order):
        return self.update_task(task_id, sort_order=int(sort_order))
    def recompute_parent_status(self, parent_task_id):
        tree = self.task_tree(parent_task_id)
        if tree is None:
            return None
        children = tree["children"]
        statuses = [str(getattr(child, "status", "pending") or "pending") for child in children]
        if not statuses:
            return tree["task"]
        if all(status == "done" for status in statuses):
            status = "done"
        elif any(status == "blocked" for status in statuses):
            status = "blocked"
        elif any(status == "in_progress" for status in statuses):
            status = "in_progress"
        elif all(status == "pending" for status in statuses):
            status = "pending"
        else:
            status = "in_progress"
        return self.update_task(parent_task_id, status=status)

    def set_task_status(self, task_id, status):
        store = self._read()
        for row in store["tasks"]:
            if int(row["id"]) == int(task_id):
                row["status"] = status
                row["updated_at"] = self._now()
                self._write(store)
                return self._object("tasks", row)
        return None

    def remember_snapshot(self, snapshot_type, title=None, content="", tags=None, task_id=None):
        return self._append(
            "snapshots",
            {
                "task_id": task_id,
                "snapshot_type": snapshot_type,
                "title": title,
                "content": content,
                "tags": tags,
            },
        )

    def snapshots(self, limit=None, task_id=None):
        rows = self._objects("snapshots")
        if task_id is not None:
            rows = [row for row in rows if str(getattr(row, "task_id", "")) == str(task_id)]
        return self._limit(rows, limit)

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

    def remember_orchestration_execution(self, execution_id, title, description, assigned_agent, root_task_id, status="pending", summary=None):
        return self._upsert(
            "orchestration_executions",
            "execution_id",
            execution_id,
            {
                "execution_id": execution_id,
                "title": title,
                "description": description,
                "assigned_agent": assigned_agent,
                "root_task_id": root_task_id,
                "status": status,
                "summary": summary,
            },
        )

    def orchestration_executions(self, limit=None):
        return self._limit(list(reversed(self._read()["orchestration_executions"])), limit)

    def orchestration_execution(self, execution_id):
        for row in self._read()["orchestration_executions"]:
            if row.get("execution_id") == execution_id:
                return row
        return None

    def remember_orchestration_task(self, task_id, execution_id, parent_id=None, dependencies=None, files=None, validation_command=None, status="pending"):
        return self._upsert(
            "orchestration_tasks",
            "task_id",
            task_id,
            {
                "task_id": task_id,
                "execution_id": execution_id,
                "parent_id": parent_id,
                "dependencies": list(dependencies or []),
                "files": list(files or []),
                "validation_command": validation_command,
                "status": status,
            },
        )

    def orchestration_task(self, task_id):
        for row in self._read()["orchestration_tasks"]:
            if row.get("task_id") == task_id:
                return row
        return None

    def orchestration_tasks(self, execution_id=None):
        rows = list(self._read()["orchestration_tasks"])
        if execution_id is not None:
            rows = [row for row in rows if row.get("execution_id") == execution_id]
        return rows

    def remember_orchestration_validation(self, task_id, command, success, output=""):
        return self._upsert(
            "orchestration_validations",
            "task_id",
            task_id,
            {
                "task_id": task_id,
                "command": command,
                "success": bool(success),
                "output": output,
            },
        )

    def orchestration_validation(self, task_id):
        for row in self._read()["orchestration_validations"]:
            if row.get("task_id") == task_id:
                return row
        return None

    def replace_orchestration_conflicts(self, execution_id, conflicts):
        store = self._read()
        rows = store["orchestration_conflicts"]
        if execution_id is not None:
            rows = [row for row in rows if row.get("execution_id") != execution_id]
        next_id = max([int(row.get("id", 0)) for row in rows] or [0]) + 1
        now = self._now()
        created: list[dict[str, object]] = []
        for conflict in conflicts:
            row = {
                "id": next_id,
                "created_at": now,
                "execution_id": execution_id,
                "kind": conflict["kind"],
                "task_ids": list(conflict.get("task_ids") or []),
                "detail": conflict.get("detail") or "",
            }
            next_id += 1
            rows.append(row)
            created.append(row)
        store["orchestration_conflicts"] = rows
        self._write(store)
        return created

    def remember_decision(self, decision_key, title, rationale, consequences, task_id=None):
        # Enforce unique decision_key constraint to match SQL backends
        store = self._read()
        for row in store["decisions"]:
            if row.get("decision_key") == decision_key and row.get("status") == "active":
                raise ValueError(f"A decision with key '{decision_key}' already exists and is active.")
        return self._append(
            "decisions",
            {
                "task_id": task_id,
                "decision_key": decision_key,
                "title": title,
                "rationale": rationale,
                "consequences": consequences,
                "status": "active",
            },
        )

    def decisions(self, status=None, limit=None, task_id=None):
        rows = self._objects("decisions")
        if status:
            rows = [row for row in rows if row.status == status]
        if task_id is not None:
            rows = [row for row in rows if str(getattr(row, "task_id", "")) == str(task_id)]
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

    def remember_command(self, agent_name, shell_type, command_text, success_flag, error_message=None, correction_applied=None, task_id=None):
        return self._append(
            "commands",
            {
                "task_id": task_id,
                "agent_name": agent_name,
                "shell_type": shell_type,
                "command_text": command_text,
                "success_flag": bool(success_flag),
                "error_message": error_message,
                "correction_applied": correction_applied,
            },
        )

    def commands(self, limit=20, success_flag=None, task_id=None):
        rows = self._objects("commands")
        if success_flag is not None:
            rows = [row for row in rows if bool(row.success_flag) == bool(success_flag)]
        if task_id is not None:
            rows = [row for row in rows if str(getattr(row, "task_id", "")) == str(task_id)]
        return self._limit(rows, limit)

    def remember_lesson(self, category, problem_description, solution_description, prevention_strategy, task_id=None):
        return self._append(
            "lessons",
            {
                "task_id": task_id,
                "category": category,
                "problem_description": problem_description,
                "solution_description": solution_description,
                "prevention_strategy": prevention_strategy,
            },
        )

    def lessons(self, category=None, limit=None, task_id=None):
        rows = self._objects("lessons")
        if category:
            rows = [row for row in rows if row.category == category]
        if task_id is not None:
            rows = [row for row in rows if str(getattr(row, "task_id", "")) == str(task_id)]
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

    def _upsert(self, collection: str, key: str, value: object, values: dict[str, object]):
        store = self._read()
        rows = store[collection]
        now = self._now()
        for row in rows:
            if row.get(key) == value:
                row.update(values)
                row.setdefault("created_at", now)
                row["updated_at"] = now
                self._write(store)
                return dict(row)
        row = {"created_at": now, "updated_at": now, **values}
        rows.append(row)
        self._write(store)
        return dict(row)

    def _objects(self, collection: str):
        rows = self._read()[collection]
        return [self._object(collection, row) for row in reversed(rows)]

    def _object(self, collection: str, row: dict[str, object]):
        model = COLLECTIONS[collection]
        if model is dict:
            return dict(row)
        if collection == "tasks":
            row = dict(row)
            row.setdefault("task_kind", "task")
            row.setdefault("sort_order", 0)
            row.setdefault("parent_task_id", None)
            row.setdefault("depends_on", None)
            row.setdefault("acceptance_criteria", None)
        return model(**row)

    def _limit(self, rows, limit):
        return rows if limit is None else rows[:limit]

    def _now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
