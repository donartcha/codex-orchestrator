from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from codex_context.backends import FileBackend, SQLiteBackend, validate_backend_contract
from codex_context.schema_migrations import TASK_SCOPE_TABLES, ensure_task_scope_columns


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

    def test_sqlite_task_scope_migration_adds_missing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = create_engine(f"sqlite:///{Path(temp_dir) / 'legacy.sqlite3'}", future=True)
            try:
                with engine.begin() as connection:
                    connection.execute(text("CREATE TABLE tasks (id INTEGER PRIMARY KEY)"))
                    connection.execute(text("CREATE TABLE context_snapshots (id INTEGER PRIMARY KEY)"))
                    connection.execute(text("CREATE TABLE architectural_decisions (id INTEGER PRIMARY KEY)"))
                    connection.execute(text("CREATE TABLE command_history (id INTEGER PRIMARY KEY)"))
                    connection.execute(text("CREATE TABLE lessons_learned (id INTEGER PRIMARY KEY)"))

                ensure_task_scope_columns(engine)

                inspector = inspect(engine)
                for table_name in TASK_SCOPE_TABLES:
                    column_names = {column["name"] for column in inspector.get_columns(table_name)}
                    self.assertIn("task_id", column_names)
            finally:
                engine.dispose()

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
        backend.remember_orchestration_execution("exec-0001", "Backend parity run", "Exercise orchestration.", "testing-agent", "root-exec-0001", "pending")
        backend.remember_orchestration_task("root-exec-0001", "exec-0001", None, [], [], None, "done")
        backend.remember_orchestration_task("phase-exec-0001-001", "exec-0001", None, ["root-exec-0001"], ["context.py"], None, "pending")
        backend.remember_orchestration_validation("root-exec-0001", "pytest tests", True, "ok")
        backend.replace_orchestration_conflicts(
            "exec-0001",
            [{"kind": "overlapping_write_scope", "task_ids": ["root-exec-0001", "phase-exec-0001-001"], "detail": "same file"}],
        )
        backend.remember_decision("backend-contract", "Use shared contract", "Normalize public methods.", "Backends stay swappable.", task_id=second_task.id)
        backend.remember_decision("global-contract", "Allow global memory", "Some memory is not task-specific.", "Task scope remains optional.")
        backend.remember_command("testing-agent", "powershell", "pytest tests\\test_backend_parity.py -v", True, task_id=second_task.id)
        backend.remember_command("testing-agent", "powershell", "pytest missing", False, "No such file", "Run focused test path.")
        backend.remember_lesson("testing", "Backend parity can drift.", "Use shared tests.", "Run parity tests per backend change.", task_id=second_task.id)
        backend.remember_lesson("testing", "Global lessons still exist.", "Store without task id.", "Only pass task id when useful.")

        return {
            "pending_tasks": _payload(backend.tasks("pending", limit=10), "title", "priority", "assigned_agent", "status"),
            "done_tasks": _payload(backend.tasks("done", limit=10), "title", "priority", "assigned_agent", "status"),
            "all_tasks": _payload(backend.tasks("all", limit=10), "title", "priority", "assigned_agent", "status"),
            "limited_tasks": _payload(backend.tasks("pending", limit=1), "title"),
            "task_logs": _payload(backend.task_logs(task_id=second_task.id, limit=10), "agent_name", "log_type", "content"),
            "orchestration_executions": [
                (
                    row["execution_id"],
                    row["title"],
                    row["assigned_agent"],
                    row["root_task_id"],
                    row["status"],
                )
                for row in backend.orchestration_executions(limit=10)
            ],
            "orchestration_tasks": sorted(
                [
                    (
                        row["task_id"],
                        row["execution_id"],
                        tuple(row["dependencies"]),
                        tuple(row["files"]),
                        row["status"],
                    )
                    for row in backend.orchestration_tasks("exec-0001")
                ]
            ),
            "orchestration_validation": (
                backend.orchestration_validation("root-exec-0001")["task_id"],
                backend.orchestration_validation("root-exec-0001")["success"],
            ),
            "decisions": _payload(backend.decisions(status="active", limit=10), "decision_key", "title", "status", "task_id"),
            "task_decisions": _payload(backend.decisions(status="active", limit=10, task_id=second_task.id), "decision_key", "task_id"),
            "failed_commands": _payload(backend.commands(limit=10, success_flag=False), "agent_name", "shell_type", "success_flag", "error_message"),
            "task_commands": _payload(backend.commands(limit=10, task_id=second_task.id), "agent_name", "task_id"),
            "lessons": _payload(backend.lessons(category="testing", limit=10), "category", "problem_description", "solution_description", "task_id"),
            "task_lessons": _payload(backend.lessons(category="testing", limit=10, task_id=second_task.id), "problem_description", "task_id"),
            "missing_task_update": backend.set_task_status(999999, "done") is None,
        }


if __name__ == "__main__":
    unittest.main()


class DecisionKeyParityTests(unittest.TestCase):
    def test_sqlite_and_file_backends_reject_duplicate_active_decision_key(self) -> None:
        """Both backends should enforce unique decision_key for active decisions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sqlite = SQLiteBackend(path=root / "memory.sqlite3")
            file_backend = FileBackend(path=root / "memory.json")

            try:
                # Test SQLite backend
                sqlite.remember_decision("unique-key-1", "First", "Rationale", "")
                with self.assertRaises(Exception) as sqlite_error:
                    sqlite.remember_decision("unique-key-1", "Duplicate", "Rationale", "")
                self.assertIn("unique", str(sqlite_error.exception).lower())

                # Test file backend
                file_backend.remember_decision("unique-key-2", "First", "Rationale", "")
                with self.assertRaises(ValueError) as file_error:
                    file_backend.remember_decision("unique-key-2", "Duplicate", "Rationale", "")
                self.assertIn("already exists", str(file_error.exception))
            finally:
                sqlite.close()
                file_backend.close()

    def test_both_backends_allow_new_decision_keys(self) -> None:
        """Both backends should allow different decision keys without issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sqlite = SQLiteBackend(path=root / "memory.sqlite3")
            file_backend = FileBackend(path=root / "memory.json")

            try:
                # Both should succeed
                dec1_sqlite = sqlite.remember_decision("key-a", "Decision A", "Rationale", "")
                dec2_sqlite = sqlite.remember_decision("key-b", "Decision B", "Rationale", "")
                dec1_file = file_backend.remember_decision("key-c", "Decision C", "Rationale", "")
                dec2_file = file_backend.remember_decision("key-d", "Decision D", "Rationale", "")

                self.assertIsNotNone(dec1_sqlite)
                self.assertIsNotNone(dec2_sqlite)
                self.assertIsNotNone(dec1_file)
                self.assertIsNotNone(dec2_file)
            finally:
                sqlite.close()
                file_backend.close()


if __name__ == "__main__":
    unittest.main()
