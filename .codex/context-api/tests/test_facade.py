from __future__ import annotations

import tempfile
import unittest
import warnings
from pathlib import Path

from codex_context.backends import FileBackend
from codex_context.context import (
    CodexContext,
    get_context_config,
    open_context,
    validate_facade_usage,
)


class FacadeTests(unittest.TestCase):
    def test_public_config_excludes_backend_internals(self) -> None:
        config = get_context_config()

        self.assertIn("open_context", config["public_api"])
        self.assertIn("CodexContext", config["public_api"])
        self.assertNotIn("Engine", config["public_api"])
        self.assertNotIn("Session", config["public_api"])
        self.assertNotIn("engine", config["public_api"])

    def test_open_context_accepts_explicit_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = FileBackend(Path(temp_dir) / "memory.json")

            with open_context(backend=backend) as context:
                self.assertIsInstance(context, CodexContext)
                self.assertEqual(context.backend_status().name, "file")

    def test_engine_property_is_deprecated_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = CodexContext(backend=FileBackend(Path(temp_dir) / "memory.json"))

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                self.assertIsNone(context.engine)

            self.assertTrue(any(item.category is DeprecationWarning for item in caught))
            context.close()

    def test_deprecated_type_import_shims_warn(self) -> None:
        namespace: dict[str, object] = {}

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exec("from codex_context.context import Engine, Session", namespace)

        self.assertIn("Engine", namespace)
        self.assertIn("Session", namespace)
        self.assertGreaterEqual(
            sum(1 for item in caught if item.category is DeprecationWarning),
            2,
        )

    def test_session_method_is_deprecated_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = CodexContext(backend=FileBackend(Path(temp_dir) / "memory.json"))

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                with self.assertRaises(RuntimeError):
                    with context.session():
                        pass

            self.assertTrue(any(item.category is DeprecationWarning for item in caught))
            context.close()

    def test_validate_facade_usage_reports_non_public_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "ok.py").write_text(
                "from codex_context.context import open_context\n",
                encoding="utf-8",
            )
            (root / "bad.py").write_text(
                "from codex_context.context import Engine\n",
                encoding="utf-8",
            )
            (root / "bypass.py").write_text(
                "from codex_context.db import create_db_engine\n",
                encoding="utf-8",
            )

            report = validate_facade_usage(root)

        self.assertFalse(report.ok)
        self.assertEqual(len(report.violations), 2)
        self.assertEqual({violation.name for violation in report.violations}, {"Engine", "create_db_engine"})


if __name__ == "__main__":
    unittest.main()
