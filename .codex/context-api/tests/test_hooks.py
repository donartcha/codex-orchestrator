from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
HOOKS_ROOT = WORKSPACE_ROOT / ".codex" / "tools" / "precommit"


def _load_hook(name: str):
    path = HOOKS_ROOT / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.hooks
def test_local_path_hook_rejects_machine_absolute_paths(tmp_path) -> None:
    hook = _load_hook("check_local_paths.py")
    bad = tmp_path / "bad.txt"
    good = tmp_path / "good.txt"
    bad.write_text("path D:\\dev\\example\\.codex", encoding="utf-8")
    good.write_text("path .codex\\context-api", encoding="utf-8")

    assert hook.check_file(bad)
    assert hook.check_file(good) == []


@pytest.mark.hooks
def test_powershell_portability_hook_rejects_bash_commands(tmp_path) -> None:
    hook = _load_hook("check_powershell_portability.py")
    bad = tmp_path / "bad.md"
    shell_script = tmp_path / "allowed.sh"
    good = tmp_path / "good.md"
    bash_mkdir = "mkdir " + "-p output\n"
    bash_remove = "rm " + "-rf output\n"
    bad.write_text(bash_mkdir + bash_remove, encoding="utf-8")
    shell_script.write_text(bash_mkdir, encoding="utf-8")
    good.write_text("New-Item -ItemType Directory -Force -Path output\n", encoding="utf-8")

    assert len(hook.check_file(bad)) == 2
    assert hook.check_file(shell_script) == []
    assert hook.check_file(good) == []


@pytest.mark.hooks
def test_forbidden_files_hook_rejects_env_venv_and_sqlite_files(tmp_path) -> None:
    hook = _load_hook("check_forbidden_files.py")

    assert hook.check_file(".codex/context-api/.env")
    assert hook.check_file(".codex/context-api/.venv/pyvenv.cfg")
    assert hook.check_file(".codex/context-api/context.sqlite3")
    assert hook.check_file(".codex/context-api/.env.example") == []
