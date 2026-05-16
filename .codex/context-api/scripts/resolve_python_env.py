from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


REQUIRED_IMPORTS = ("typer", "sqlalchemy", "pymysql")
OPTIONAL_IMPORTS = ("dotenv", "rich")
CONTEXT_API_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = CONTEXT_API_ROOT.parents[1]


@dataclass
class PythonCandidate:
    label: str
    path: str
    exists: bool
    runnable: bool = False
    version: str = ""
    is_active_virtualenv: bool = False
    is_workspace_virtualenv: bool = False
    missing_imports: list[str] = field(default_factory=list)
    broken_imports: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PythonResolution:
    selected_python: str
    reason: str
    fallback_applied: bool
    fallback_from: str
    warnings: list[str]
    candidates: list[PythonCandidate]

    @property
    def status(self) -> str:
        if not self.selected_python:
            return "ERROR"
        if self.fallback_applied:
            return "FALLBACK_USED"
        if self.warnings:
            return "WARNING"
        return "OK"

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status
        return payload


def _dedupe_paths(paths: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    seen: set[str] = set()
    result: list[tuple[str, Path]] = []
    for label, path in paths:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append((label, path))
    return result


def _run(command: list[str], cwd: Path | None = None, timeout: int = 8) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _candidate_paths() -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []

    workspace_venv = CONTEXT_API_ROOT / ".venv" / "Scripts" / "python.exe"
    paths.append(("workspace .venv", workspace_venv))

    active_venv = os.environ.get("VIRTUAL_ENV")
    if active_venv:
        paths.append(("active virtualenv", Path(active_venv) / "Scripts" / "python.exe"))
        paths.append(("active virtualenv posix", Path(active_venv) / "bin" / "python"))

    poetry = shutil.which("poetry")
    if poetry:
        result = _run([poetry, "env", "info", "--path"], cwd=CONTEXT_API_ROOT)
        if result and result.returncode == 0 and result.stdout.strip():
            poetry_env = Path(result.stdout.strip())
            paths.append(("poetry", poetry_env / "Scripts" / "python.exe"))
            paths.append(("poetry posix", poetry_env / "bin" / "python"))

    uv = shutil.which("uv")
    if uv:
        result = _run([uv, "python", "find"], cwd=CONTEXT_API_ROOT)
        if result and result.returncode == 0 and result.stdout.strip():
            paths.append(("uv", Path(result.stdout.strip())))

    pyenv = shutil.which("pyenv")
    if pyenv:
        result = _run([pyenv, "which", "python"], cwd=CONTEXT_API_ROOT)
        if result and result.returncode == 0 and result.stdout.strip():
            paths.append(("pyenv", Path(result.stdout.strip())))

    if sys.executable:
        paths.append(("current python", Path(sys.executable)))

    system_python = shutil.which("python")
    if system_python:
        paths.append(("system python", Path(system_python)))

    py_launcher = shutil.which("py")
    if py_launcher:
        result = _run([py_launcher, "-3", "-c", "import sys; print(sys.executable)"], cwd=CONTEXT_API_ROOT)
        if result and result.returncode == 0 and result.stdout.strip():
            paths.append(("py launcher", Path(result.stdout.strip())))

    return _dedupe_paths(paths)


def _inspect_candidate(label: str, path: Path) -> PythonCandidate:
    candidate = PythonCandidate(
        label=label,
        path=str(path),
        exists=path.exists(),
        is_active_virtualenv=bool(os.environ.get("VIRTUAL_ENV") and str(path).lower().startswith(os.environ["VIRTUAL_ENV"].lower())),
        is_workspace_virtualenv=str(path).lower() == str(CONTEXT_API_ROOT / ".venv" / "Scripts" / "python.exe").lower(),
    )
    if not candidate.exists:
        candidate.warnings.append("interpreter path does not exist")
        return candidate

    probe = (
        "import importlib.util, json, sys; "
        f"mods={list(REQUIRED_IMPORTS + OPTIONAL_IMPORTS)!r}; "
        "missing=[m for m in mods if importlib.util.find_spec(m) is None]; "
        "broken=[]; "
        "\nfor m in mods:\n"
        "    try:\n"
        "        __import__(m)\n"
        "    except Exception as exc:\n"
        "        broken.append(f'{m}: {type(exc).__name__}: {exc}')\n"
        "print(json.dumps({'version': sys.version.split()[0], 'missing': missing, 'broken': broken}))"
    )
    result = _run([str(path), "-c", probe], cwd=CONTEXT_API_ROOT)
    if result is None:
        candidate.warnings.append("interpreter could not be executed")
        return candidate
    if result.returncode != 0:
        candidate.warnings.append((result.stderr or result.stdout or "interpreter probe failed").strip())
        return candidate

    candidate.runnable = True
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        candidate.warnings.append("interpreter probe returned non-json output")
        return candidate

    candidate.version = str(data.get("version", ""))
    missing = [str(item) for item in data.get("missing", [])]
    candidate.missing_imports = [item for item in missing if item in REQUIRED_IMPORTS]
    missing_optional = [item for item in missing if item in OPTIONAL_IMPORTS]
    if missing_optional:
        candidate.warnings.append(f"missing optional imports: {', '.join(missing_optional)}")
    candidate.broken_imports = [str(item) for item in data.get("broken", [])]
    return candidate


def resolve_python_environment() -> PythonResolution:
    candidates = [_inspect_candidate(label, path) for label, path in _candidate_paths()]
    warnings: list[str] = []

    current = Path(sys.executable).resolve() if sys.executable else None
    selected: PythonCandidate | None = None
    for candidate in candidates:
        if candidate.runnable and not candidate.missing_imports and not candidate.broken_imports:
            selected = candidate
            break

    if selected is None:
        for candidate in candidates:
            if candidate.runnable:
                selected = candidate
                warnings.append("No candidate had all required imports; selected first runnable interpreter.")
                break

    if selected is None:
        return PythonResolution(
            selected_python="",
            reason="No runnable Python interpreter found.",
            fallback_applied=False,
            fallback_from=str(sys.executable or ""),
            warnings=["No runnable interpreter candidates were available."],
            candidates=candidates,
        )

    fallback_from = ""
    fallback_applied = False
    if current and Path(selected.path).resolve() != current:
        fallback_applied = True
        fallback_from = str(current)

    if selected.missing_imports:
        warnings.append(f"Selected interpreter is missing required imports: {', '.join(selected.missing_imports)}")
    if selected.broken_imports:
        warnings.extend(selected.broken_imports)
    for candidate in candidates:
        if candidate.runnable and candidate.missing_imports:
            warnings.append(f"{candidate.label} missing required imports: {', '.join(candidate.missing_imports)}")

    reason = f"Selected {selected.label}"
    if selected.is_workspace_virtualenv:
        reason += " because workspace-local .venv has required imports"
    elif not selected.missing_imports:
        reason += " because it has required imports"

    return PythonResolution(
        selected_python=selected.path,
        reason=reason,
        fallback_applied=fallback_applied,
        fallback_from=fallback_from,
        warnings=warnings,
        candidates=candidates,
    )


def print_human(resolution: PythonResolution) -> None:
    print(f"Status: {resolution.status}")
    print(f"Selected Python: {resolution.selected_python or '(none)'}")
    print(f"Reason: {resolution.reason}")
    print(f"Fallback applied: {resolution.fallback_applied}")
    if resolution.fallback_from:
        print(f"Fallback from: {resolution.fallback_from}")
    if resolution.warnings:
        print("Warnings:")
        for warning in resolution.warnings:
            print(f"- {warning}")
    print("Candidates:")
    for candidate in resolution.candidates:
        missing = ", ".join(candidate.missing_imports) if candidate.missing_imports else "none"
        broken = "; ".join(candidate.broken_imports) if candidate.broken_imports else "none"
        print(
            f"- {candidate.label}: {candidate.path} | exists={candidate.exists} "
            f"runnable={candidate.runnable} version={candidate.version or 'unknown'} "
            f"missing_required={missing} broken_imports={broken}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve the best Python interpreter for Codex context tooling.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    resolution = resolve_python_environment()
    if args.json:
        print(json.dumps(resolution.to_dict(), indent=2))
    else:
        print_human(resolution)
    return 1 if resolution.status == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
