from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from resolve_python_env import resolve_python_environment


CONTEXT_API_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = CONTEXT_API_ROOT.parents[1]
CONTEXT_MIRROR = WORKSPACE_ROOT / ".codex" / "context"


@dataclass
class RuntimeCheck:
    name: str
    status: str
    message: str


@dataclass
class RuntimeValidation:
    status: str
    active_interpreter: str
    active_shell: str
    fallback_state: str
    warnings: list[str]
    checks: list[RuntimeCheck]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _check_import(module_name: str, python_path: str) -> RuntimeCheck:
    result = subprocess.run(
        [python_path, "-c", f"import {module_name}"],
        cwd=str(CONTEXT_API_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "import failed").strip()
        return RuntimeCheck("required import", "ERROR", f"{module_name}: {message}")
    return RuntimeCheck("required import", "OK", module_name)


def _detect_shell() -> str:
    if os.environ.get("PSModulePath"):
        return "powershell"
    if os.environ.get("COMSPEC"):
        return "cmd-or-powershell"
    return platform.system().lower() or "unknown"


def _check_powershell() -> RuntimeCheck:
    executable = shutil.which("powershell") or shutil.which("pwsh")
    if executable:
        return RuntimeCheck("PowerShell", "OK", executable)
    if platform.system().lower() == "windows":
        return RuntimeCheck("PowerShell", "WARNING", "PowerShell executable was not found on PATH.")
    return RuntimeCheck("PowerShell", "WARNING", "PowerShell is not the active platform shell.")


def _check_codex_memory() -> RuntimeCheck:
    path = CONTEXT_API_ROOT / "codex_memory.py"
    if path.exists():
        return RuntimeCheck("codex_memory.py", "OK", str(path))
    return RuntimeCheck("codex_memory.py", "ERROR", "codex_memory.py is missing.")


def _check_filesystem() -> RuntimeCheck:
    try:
        with tempfile.NamedTemporaryFile(prefix="codex-runtime-", dir=CONTEXT_API_ROOT, delete=True) as handle:
            handle.write(b"ok")
        return RuntimeCheck("filesystem permissions", "OK", f"Writable: {CONTEXT_API_ROOT}")
    except Exception as exc:
        return RuntimeCheck("filesystem permissions", "ERROR", f"{type(exc).__name__}: {exc}")


def _check_utf8() -> RuntimeCheck:
    sample = "Codex UTF-8 check"
    try:
        sample.encode("utf-8").decode("utf-8")
    except UnicodeError as exc:
        return RuntimeCheck("UTF-8 compatibility", "ERROR", str(exc))
    encoding = sys.stdout.encoding or "unknown"
    if encoding.lower().replace("-", "") != "utf8":
        return RuntimeCheck("UTF-8 compatibility", "WARNING", f"stdout encoding is {encoding}; UTF-8 data still round-trips.")
    return RuntimeCheck("UTF-8 compatibility", "OK", f"stdout encoding is {encoding}")


def _check_memory_backend(python_path: str) -> RuntimeCheck:
    probe = f"""
import sys
sys.path.insert(0, {str(CONTEXT_API_ROOT)!r})
from codex_context.context import open_context
with open_context() as context:
    context.tasks(status='pending', limit=1)
    status = context.backend_status()
print(status.name + '|' + str(status.degraded))
"""
    result = subprocess.run(
        [python_path, "-c", probe],
        cwd=str(CONTEXT_API_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "memory backend probe failed").strip()
        if CONTEXT_MIRROR.exists():
            return RuntimeCheck(
                "memory backend",
                "FALLBACK_USED",
                f"{message}. The context API will use the best available backend.",
            )
        return RuntimeCheck("memory backend", "ERROR", message)
    stdout = (result.stdout or "").strip()
    if "|True" in stdout:
        return RuntimeCheck("memory backend", "FALLBACK_USED", f"open_context() selected fallback backend: {stdout}")
    return RuntimeCheck("memory backend", "OK", f"open_context() selected backend: {stdout}")


def _check_shell_compatibility() -> RuntimeCheck:
    if platform.system().lower() != "windows":
        return RuntimeCheck("shell compatibility", "WARNING", "Workspace policy expects PowerShell on Windows.")
    return RuntimeCheck("shell compatibility", "OK", "Windows shell policy applies; prefer PowerShell cmdlets.")


def _overall_status(checks: list[RuntimeCheck], resolver_status: str) -> str:
    if any(check.status == "ERROR" for check in checks):
        return "ERROR"
    if resolver_status == "FALLBACK_USED" or any(check.status == "FALLBACK_USED" for check in checks):
        return "FALLBACK_USED"
    if resolver_status == "WARNING" or any(check.status == "WARNING" for check in checks):
        return "WARNING"
    return "OK"


def validate_runtime() -> RuntimeValidation:
    resolution = resolve_python_environment()
    selected_python = resolution.selected_python or sys.executable
    checks: list[RuntimeCheck] = [
        RuntimeCheck("Python interpreter", resolution.status, resolution.reason),
        RuntimeCheck("virtualenv", "OK" if ".venv" in selected_python else "WARNING", selected_python),
        _check_powershell(),
        _check_codex_memory(),
        _check_filesystem(),
        _check_utf8(),
        _check_shell_compatibility(),
    ]
    for module_name in ("typer", "sqlalchemy", "pymysql"):
        checks.append(_check_import(module_name, selected_python))
    checks.append(_check_memory_backend(selected_python))

    status = _overall_status(checks, resolution.status)
    fallback_state = "fallback used" if resolution.fallback_applied or any(c.status == "FALLBACK_USED" for c in checks) else "none"
    warnings = list(resolution.warnings)
    warnings.extend(check.message for check in checks if check.status in {"WARNING", "FALLBACK_USED"})

    return RuntimeValidation(
        status=status,
        active_interpreter=selected_python,
        active_shell=_detect_shell(),
        fallback_state=fallback_state,
        warnings=warnings,
        checks=checks,
    )


def print_human(validation: RuntimeValidation) -> None:
    print(f"Runtime status: {validation.status}")
    print(f"Active interpreter: {validation.active_interpreter}")
    print(f"Active shell: {validation.active_shell}")
    print(f"Fallback state: {validation.fallback_state}")
    if validation.warnings:
        print("Warnings:")
        for warning in validation.warnings:
            print(f"- {warning}")
    print("Checks:")
    for check in validation.checks:
        print(f"- {check.status}: {check.name}: {check.message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Codex context runtime.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    validation = validate_runtime()
    if args.json:
        print(json.dumps(validation.to_dict(), indent=2))
    else:
        print_human(validation)
    return 1 if validation.status == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
