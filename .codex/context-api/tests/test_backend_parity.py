from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from codex_context.backends import FileBackend, SQLiteBackend, validate_backend_contract


def _payload(rows: list[object], *fields: str) -> list[tuple[object, ...]]:
    return [tuple(getattr(row, field) for field in fields) for row in rows]


class BackendParityTests(unittest.TestCase):
    def test_sqlite_and_file_backends_satisfy_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backends = [
                SQLiteBackend(path=root / "memory.sqlite3"),
                FileBackend(path=root / "memory.json"),
            ]

            try:
                for backend in backends:
                    report = validate_backend_contract(backend)
                    self.assertTrue(report.ok, f"{report.backend_name} missing {report.missing_methods}")
            finally:
                for backend in backends:
                    backend.close()

    def test_sqlite_and_file_backends_match_core_operations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sqlite = SQLiteBackend(path=root / "memory.sqlite3")
            file_backend = FileBackend(path=root / "memory.json")

            try:
                sqlite_snapshot = self._exercise_backend(sqlite)
                file_snapshot = self._exercise_backend(file_backend)
            finally:
                sqlite.close()
                file_backend.close()

        self.assertEqual(sqlite_snapshot, file_snapshot)

    def _exercise_backend(self, backend) -> dict[str, object]:
        first_task = backend.remember_task(
            "Investigate contract",
            "Define normalized backend surface.",
            "testing-agent",
            "high",
        )
        second_task = backend.remember_task(
            "Write parity tests",
            "Check shared operations.",
            "testing-agent",
            "normal",
        )
        backend.set_task_status(first_task.id, "done")
        backend.remember_task_log(second_task.id, "Created parity checks.", "testing-agent", "validation")
        backend.remember_task_log(second_task.id, "Reviewed results.", "reviewer-agent", "review")
        backend.remember_decision("backend-contract", "Use shared contract", "Normalize public methods.", "Backends stay swappable.")
        backend.remember_command("testing-agent", "powershell", "pytest tests\\test_backend_parity.py -v", True)
        backend.remember_command("testing-agent", "powershell", "pytest missing", False, "No such file", "Run focused test path.")
        backend.remember_lesson("testing", "Backend parity can drift.", "Use shared tests.", "Run parity tests per backend change.")

        return {
            "pending_tasks": _payload(backend.tasks("pending", limit=10), "title", "priority", "assigned_agent", "status"),
            "done_tasks": _payload(backend.tasks("done", limit=10), "title", "priority", "assigned_agent", "status"),
            "limited_tasks": _payload(backend.tasks("pending", limit=1), "title"),
            "task_logs": _payload(backend.task_logs(task_id=second_task.id, limit=10), "agent_name", "log_type", "content"),
            "decisions": _payload(backend.decisions(status="active", limit=10), "decision_key", "title", "status"),
            "failed_commands": _payload(backend.commands(limit=10, success_flag=False), "agent_name", "shell_type", "success_flag", "error_message"),
            "lessons": _payload(backend.lessons(category="testing", limit=10), "category", "problem_description", "solution_description"),
            "missing_task_update": backend.set_task_status(999999, "done") is None,
        }


if __name__ == "__main__":
    unittest.main()
