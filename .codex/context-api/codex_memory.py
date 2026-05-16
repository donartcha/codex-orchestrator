from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CONTEXT_API_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = CONTEXT_API_ROOT / "scripts"
MINIMUM_CLI_IMPORTS = ("typer", "rich", "sqlalchemy", "pymysql")
FALLBACK_ENV_FLAG = "CODEX_MEMORY_PYTHON_FALLBACK_ATTEMPTED"


def _missing_cli_imports() -> list[str]:
    missing: list[str] = []
    for module_name in MINIMUM_CLI_IMPORTS:
        try:
            __import__(module_name)
        except Exception:
            missing.append(module_name)
    return missing


def _resolve_fallback_python() -> tuple[str, bool, list[str]]:
    resolver = SCRIPTS_ROOT / "resolve_python_env.py"
    if not resolver.exists():
        return "", False, ["resolve_python_env.py is unavailable"]
    try:
        result = subprocess.run(
            [sys.executable, str(resolver), "--json"],
            cwd=str(CONTEXT_API_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return "", False, [f"resolver failed: {type(exc).__name__}: {exc}"]
    if result.returncode != 0 and not result.stdout.strip():
        return "", False, [result.stderr.strip() or "resolver returned no output"]
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return "", False, ["resolver returned non-json output"]
    return (
        str(payload.get("selected_python") or ""),
        bool(payload.get("fallback_applied")),
        [str(item) for item in payload.get("warnings", [])],
    )


def _maybe_reexec_with_resolved_python() -> None:
    missing = _missing_cli_imports()
    if not missing:
        return
    if os.environ.get(FALLBACK_ENV_FLAG):
        return
    selected_python, _fallback_applied, warnings = _resolve_fallback_python()
    if not selected_python:
        warning_text = "; ".join(warnings)
        print(f"codex_memory.py missing imports: {', '.join(missing)}", file=sys.stderr)
        if warning_text:
            print(f"Python resolution warning: {warning_text}", file=sys.stderr)
        return
    if Path(selected_python).resolve() == Path(sys.executable).resolve():
        return
    env = os.environ.copy()
    env[FALLBACK_ENV_FLAG] = "1"
    env["CODEX_MEMORY_FALLBACK_FROM"] = sys.executable
    env["CODEX_MEMORY_FALLBACK_TO"] = selected_python
    env["CODEX_MEMORY_FALLBACK_REASON"] = f"missing imports: {', '.join(missing)}"
    result = subprocess.run(
        [selected_python, str(Path(__file__).resolve()), *sys.argv[1:]],
        cwd=str(CONTEXT_API_ROOT),
        env=env,
        check=False,
    )
    raise SystemExit(result.returncode)


_maybe_reexec_with_resolved_python()

import typer

from codex_context.config import ConfigError
from codex_context.context import open_context
from codex_context.orchestration import OrchestrationStore

sys.path.insert(0, str(SCRIPTS_ROOT))
from resolve_python_env import resolve_python_environment
from runtime_validation import validate_runtime


app = typer.Typer(help="Official Codex persistent memory CLI.")
task_app = typer.Typer(help="Manage tasks and task logs.")
decision_app = typer.Typer(help="Manage architectural and technical decisions.")
lesson_app = typer.Typer(help="Manage reusable lessons.")
command_app = typer.Typer(help="Manage command history.")
snapshot_app = typer.Typer(help="Manage memory snapshots.")
memory_app = typer.Typer(help="Inspect memory lifecycle reports.")
contradictions_app = typer.Typer(help="Inspect memory contradictions.")
orchestration_app = typer.Typer(help="Manage structured orchestration tasks and execution.")

app.add_typer(task_app, name="task")
app.add_typer(decision_app, name="decision")
app.add_typer(lesson_app, name="lesson")
app.add_typer(command_app, name="command")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(memory_app, name="memory")
app.add_typer(contradictions_app, name="contradictions")
app.add_typer(orchestration_app, name="orchestrate")

def _emit(message: object = "") -> None:
    print(str(message), flush=False)


def _section(title: str) -> None:
    _emit(f"\n== {title} ==")


def _clip(value: object, limit: int = 100) -> str:
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _run_memory_call(callable_obj):
    try:
        return callable_obj()
    except ConfigError as exc:
        _emit(f"Configuration error: {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        _emit("Memory operation failed.")
        _emit("The context API could not open any memory backend. Secrets were not printed.")
        _emit(f"Error type: {type(exc).__name__}")
        _emit(f"Message: {_clip(exc, 240)}")
        raise typer.Exit(1) from exc


def _print_runtime_panel() -> None:
    resolution = resolve_python_environment()
    validation = validate_runtime()
    fallback_from = os.environ.get("CODEX_MEMORY_FALLBACK_FROM") or resolution.fallback_from
    fallback_to = os.environ.get("CODEX_MEMORY_FALLBACK_TO") or resolution.selected_python
    fallback_state = "fallback used" if fallback_from else validation.fallback_state
    runtime_status = "FALLBACK_USED" if fallback_from else validation.status
    _section("Runtime environment")
    _emit(f"Runtime status: {runtime_status}")
    _emit(f"Active interpreter: {validation.active_interpreter or '(none)'}")
    _emit(f"Active shell: {validation.active_shell}")
    _emit(f"Fallback state: {fallback_state}")
    _emit(f"Python fallback applied: {bool(fallback_from) or resolution.fallback_applied}")
    _emit(f"Python reason: {resolution.reason}")
    if fallback_from:
        _emit(f"Fallback from: {fallback_from}")
    if fallback_to:
        _emit(f"Fallback to: {fallback_to}")
    if validation.warnings:
        _emit("Environment warnings:")
        for warning in validation.warnings:
            _emit(f"- {_clip(warning, 180)}")


def _print_backend_panel(context) -> None:
    status = context.backend_status()
    _section("Memory backend")
    _emit(f"Active backend: {status.name}")
    _emit(f"Degraded: {status.degraded}")
    if status.warning:
        _emit(f"Warning: {status.warning}")
    for key, value in status.details.items():
        _emit(f"{key}: {value}")
    attempts = context.backend_attempts()
    if attempts:
        _emit("Attempts:")
        for attempt in attempts:
            label = "active" if attempt.active else "unavailable"
            message = f" - {attempt.name}: {label}"
            if attempt.warning:
                message = f"{message} ({_clip(attempt.warning, 140)})"
            _emit(message)


def _record_fallback_lesson_if_present() -> None:
    fallback_from = os.environ.get("CODEX_MEMORY_FALLBACK_FROM", "")
    fallback_to = os.environ.get("CODEX_MEMORY_FALLBACK_TO", "")
    reason = os.environ.get("CODEX_MEMORY_FALLBACK_REASON", "")
    if not fallback_from or not fallback_to:
        return
    try:
        with open_context() as context:
            context.remember_fallback_event(
                agent_name="codex_memory",
                shell_type="powershell",
                command_text=" ".join([Path(sys.executable).name, Path(__file__).name, *sys.argv[1:]]),
                fallback_from=fallback_from,
                fallback_to=fallback_to,
                reason=reason,
            )
            context.remember_recovery_lesson(
                category="python-environment",
                problem_description=f"Python interpreter could not run codex_memory.py because {reason}.",
                solution_description="Resolve the workspace Python environment and re-run with the selected local interpreter.",
                prevention_strategy="Run `python codex_memory.py resolve-python` or use `.\\.venv\\Scripts\\python.exe` from `.codex\\context-api`.",
            )
    except Exception:
        # Fallback recording is helpful but must not block the requested command.
        return


def _print_tasks(tasks, title: str) -> None:
    _section(title)
    for task in tasks:
        _emit(
            f"- #{task.id} [{task.status or ''}/{task.priority or ''}] "
            f"{task.assigned_agent or ''}: {_clip(task.title, 80)} ({task.created_at})"
        )
    _emit(f"{len(tasks)} task(s).")


def _print_task_logs(task_logs, title: str) -> None:
    _section(title)
    for task_log in task_logs:
        _emit(
            f"- #{task_log.id} task={task_log.task_id} {task_log.agent_name or ''} "
            f"{task_log.log_type or ''}: {_clip(task_log.content, 100)} ({task_log.created_at})"
        )
    _emit(f"{len(task_logs)} task log(s).")


def _print_decisions(decisions, title: str) -> None:
    _section(title)
    for decision in decisions:
        _emit(
            f"- #{decision.id} [{decision.status or ''}] {_clip(decision.decision_key, 40)}: "
            f"{_clip(decision.title, 80)} ({decision.created_at})"
        )
    _emit(f"{len(decisions)} decision(s).")


def _print_lessons(lessons, title: str) -> None:
    _section(title)
    for lesson in lessons:
        _emit(f"- #{lesson.id} [{lesson.category or ''}] {_clip(lesson.problem_description, 100)} ({lesson.created_at})")
    _emit(f"{len(lessons)} lesson(s).")


def _print_commands(commands, title: str) -> None:
    _section(title)
    for command in commands:
        _emit(
            f"- #{command.id} {command.agent_name or ''}/{command.shell_type or ''} "
            f"ok={bool(command.success_flag)} command={_clip(command.command_text, 80)} "
            f"error={_clip(command.error_message, 80)} ({command.created_at})"
        )
    _emit(f"{len(commands)} command(s).")


def _print_snapshots(snapshots, title: str) -> None:
    _section(title)
    for snapshot in snapshots:
        _emit(
            f"- #{snapshot.id} [{snapshot.snapshot_type or ''}] "
            f"{_clip(snapshot.title, 80)} ({snapshot.created_at})"
        )
    _emit(f"{len(snapshots)} snapshot(s).")


@app.command()
def check() -> None:
    """Check that the official context API can open a backend without printing secrets."""
    def call() -> None:
        with open_context() as context:
            context.tasks("pending", limit=1)
            _emit(f"Context OK backend={context.backend_status().name}")

    _run_memory_call(call)


@app.command()
def bootstrap(
    limit: int = typer.Option(5, "--limit", "-n", min=1, help="Rows to show per section."),
    status: str = typer.Option("pending", "--status", "-s", help="Task status to show."),
    lesson_category: str = typer.Option("", "--lesson-category", "-c", help="Optional lesson category filter."),
) -> None:
    """Show the memory bundle Codex should read before work."""
    def call() -> None:
        _record_fallback_lesson_if_present()
        _section("Codex memory bootstrap")
        _print_runtime_panel()
        with open_context() as context:
            _print_backend_panel(context)
            tasks = context.tasks(status, limit=limit)
            decisions = context.decisions(limit=limit)
            lessons = context.lessons(lesson_category or None, limit=limit)
            failed_commands = context.commands(limit=limit, success_flag=False)
        _print_tasks(tasks, f"Tasks ({status})")
        _print_decisions(decisions, "Recent decisions")
        _print_lessons(lessons, "Recent lessons")
        _print_commands(failed_commands, "Recent failed commands")

    _run_memory_call(call)


@app.command("runtime-check")
def runtime_check() -> None:
    """Run full runtime validation."""
    _record_fallback_lesson_if_present()
    validation = validate_runtime()
    fallback_from = os.environ.get("CODEX_MEMORY_FALLBACK_FROM", "")
    status = "FALLBACK_USED" if fallback_from else validation.status
    fallback_state = "fallback used" if fallback_from else validation.fallback_state
    _section("Codex runtime validation")
    _emit(f"Status: {status}")
    _emit(f"Active interpreter: {validation.active_interpreter}")
    _emit(f"Active shell: {validation.active_shell}")
    _emit(f"Fallback state: {fallback_state}")
    if fallback_from:
        _emit(f"Fallback from: {fallback_from}")
        _emit(f"Fallback to: {os.environ.get('CODEX_MEMORY_FALLBACK_TO', validation.active_interpreter)}")
    _section("Runtime checks")
    for check in validation.checks:
        _emit(f"- {check.status}: {check.name}: {_clip(check.message, 160)}")
    if validation.warnings:
        _emit("Warnings:")
        for warning in validation.warnings:
            _emit(f"- {_clip(warning, 180)}")
    if validation.status == "ERROR":
        raise typer.Exit(1)


@app.command("resolve-python")
def resolve_python() -> None:
    """Resolve the preferred Python interpreter and show fallbacks."""
    _record_fallback_lesson_if_present()
    resolution = resolve_python_environment()
    _section("Codex Python environment resolution")
    _emit(f"Status: {resolution.status}")
    _emit(f"Selected Python: {resolution.selected_python or '(none)'}")
    _emit(f"Reason: {resolution.reason}")
    _emit(f"Fallback applied: {resolution.fallback_applied}")
    if resolution.fallback_from:
        _emit(f"Fallback from: {resolution.fallback_from}")
    if resolution.warnings:
        _emit("Warnings:")
        for warning in resolution.warnings:
            _emit(f"- {_clip(warning, 180)}")
    _section("Python candidates")
    for candidate in resolution.candidates:
        _emit(
            f"- {candidate.label}: {_clip(candidate.path, 80)} runnable={candidate.runnable} "
            f"version={candidate.version or ''} missing={', '.join(candidate.missing_imports) or 'none'} "
            f"broken={_clip('; '.join(candidate.broken_imports) or 'none', 120)}"
        )
    if resolution.status == "ERROR":
        raise typer.Exit(1)


@app.command("env-status")
def env_status() -> None:
    """Show shell, Python, MariaDB and fallback status."""
    _record_fallback_lesson_if_present()
    _print_runtime_panel()
    def call() -> None:
        with open_context() as context:
            _print_backend_panel(context)

    _run_memory_call(call)


@app.command("backend-status")
def backend_status() -> None:
    """Show the selected memory backend and attempted fallback chain."""
    def call() -> None:
        with open_context() as context:
            _print_backend_panel(context)

    _run_memory_call(call)


@app.command()
def finish(
    task_id: int = typer.Option(..., "--task-id", "-t", help="Task id to summarize."),
    summary: str = typer.Option(..., "--summary", help="Task completion summary."),
    status: str = typer.Option("", "--status", "-s", help="Optional new task status."),
    agent: str = typer.Option("codex", "--agent", "-a", help="Agent writing the summary."),
    log_type: str = typer.Option("summary", "--type", help="Task log type."),
) -> None:
    """Record the memory updates Codex should write after work."""
    def call() -> None:
        with open_context() as context:
            task_log = context.remember_task_log(task_id, summary, agent_name=agent or None, log_type=log_type)
            task = context.set_task_status(task_id, status) if status else None
        _emit(f"Task log recorded id={task_log.id} task_id={task_log.task_id}")
        if status:
            if task is None:
                _emit(f"Task not found: {task_id}")
                raise typer.Exit(1)
            _emit(f"Task updated id={task.id} status={task.status}")

    _run_memory_call(call)


@app.command()
def status() -> None:
    """Show a compact memory status overview."""
    def call() -> None:
        with open_context() as context:
            pending = context.tasks("pending", limit=5)
            recent_decisions = context.decisions(limit=5)
            recent_lessons = context.lessons(limit=5)
            failed_commands = context.commands(limit=5, success_flag=False)
            recent_logs = context.task_logs(limit=5)
        _section("Codex memory status")
        _emit(f"Pending tasks shown: {len(pending)}")
        _emit(f"Recent decisions shown: {len(recent_decisions)}")
        _emit(f"Recent lessons shown: {len(recent_lessons)}")
        _emit(f"Recent failed commands shown: {len(failed_commands)}")
        _emit(f"Recent task logs shown: {len(recent_logs)}")

    _run_memory_call(call)


@task_app.command("add")
def task_add(
    title: str = typer.Option(..., "--title", help="Task title."),
    description: str = typer.Option(..., "--description", help="Task description."),
    agent: str = typer.Option("", "--agent", "-a", help="Assigned agent."),
    priority: str = typer.Option("normal", "--priority", "-p", help="Task priority."),
) -> None:
    """Add a task."""
    def call() -> None:
        with open_context() as context:
            task = context.remember_task(title, description, assigned_agent=agent or None, priority=priority)
        _emit(f"Task added id={task.id} title={task.title!r}")

    _run_memory_call(call)


@task_app.command("list")
def task_list(
    status: str = typer.Option("pending", "--status", "-s", help="Task status."),
    limit: int = typer.Option(20, "--limit", "-n", min=1, help="Maximum rows."),
) -> None:
    """List tasks by status."""
    def call() -> None:
        with open_context() as context:
            tasks = context.tasks(status, limit=limit)
        _print_tasks(tasks, f"Tasks ({status})")

    _run_memory_call(call)


@task_app.command("status")
def task_status(
    task_id: int = typer.Option(..., "--task-id", "-t", help="Task id."),
    status: str = typer.Option(..., "--status", "-s", help="New task status."),
) -> None:
    """Update task status."""
    def call() -> None:
        with open_context() as context:
            task = context.set_task_status(task_id, status)
        if task is None:
            _emit(f"Task not found: {task_id}")
            raise typer.Exit(1)
        _emit(f"Task updated id={task.id} status={task.status}")

    _run_memory_call(call)


@task_app.command("log")
def task_log(
    task_id: int = typer.Option(..., "--task-id", "-t", help="Task id."),
    content: str = typer.Option(..., "--content", help="Task log content."),
    agent: str = typer.Option("", "--agent", "-a", help="Agent name."),
    log_type: str = typer.Option("summary", "--type", help="Task log type."),
) -> None:
    """Add a task log."""
    def call() -> None:
        with open_context() as context:
            task_log = context.remember_task_log(task_id, content, agent_name=agent or None, log_type=log_type)
        _emit(f"Task log added id={task_log.id} task_id={task_log.task_id}")

    _run_memory_call(call)


@task_app.command("logs")
def task_logs(
    task_id: int | None = typer.Option(None, "--task-id", "-t", help="Optional task id."),
    agent: str = typer.Option("", "--agent", "-a", help="Optional agent filter."),
    log_type: str = typer.Option("", "--type", help="Optional log type filter."),
    limit: int = typer.Option(20, "--limit", "-n", min=1, help="Maximum rows."),
) -> None:
    """List task logs."""
    def call() -> None:
        with open_context() as context:
            logs = context.task_logs(
                task_id=task_id,
                agent_name=agent or None,
                log_type=log_type or None,
                limit=limit,
            )
        _print_task_logs(logs, "Task logs")

    _run_memory_call(call)


@decision_app.command("add")
def decision_add(
    key: str = typer.Option(..., "--key", help="Stable unique decision key."),
    title: str = typer.Option(..., "--title", help="Decision title."),
    rationale: str = typer.Option(..., "--rationale", help="Why this decision was taken."),
    consequences: str = typer.Option("", "--consequences", help="Expected consequences."),
) -> None:
    """Add a decision."""
    def call() -> None:
        with open_context() as context:
            decision = context.remember_decision(key, title, rationale, consequences)
        _emit(f"Decision added id={decision.id} key={decision.decision_key!r}")

    _run_memory_call(call)


@decision_app.command("list")
def decision_list(
    limit: int = typer.Option(10, "--limit", "-n", min=1, help="Maximum rows."),
    status: str = typer.Option("", "--status", "-s", help="Optional decision status."),
) -> None:
    """List decisions."""
    def call() -> None:
        with open_context() as context:
            decisions = context.decisions(status or None, limit=limit)
        _print_decisions(decisions, "Decisions")

    _run_memory_call(call)


@decision_app.command("supersede")
def decision_supersede(
    old_id: int = typer.Argument(..., help="Decision id to mark superseded."),
    new_id: int = typer.Argument(..., help="Replacement decision id."),
) -> None:
    """Mark an older decision as superseded by a newer decision."""
    def call() -> None:
        with open_context() as context:
            decision = context.supersede_decision(old_id, new_id)
        if decision is None:
            _emit("Decision supersession failed; verify both ids exist.")
            raise typer.Exit(1)
        _emit(f"Decision superseded id={decision.id} status={decision.status}")

    _run_memory_call(call)


@lesson_app.command("add")
def lesson_add(
    category: str = typer.Option(..., "--category", "-c", help="Lesson category."),
    problem: str = typer.Option(..., "--problem", help="Problem description."),
    solution: str = typer.Option(..., "--solution", help="Solution description."),
    prevention: str = typer.Option(..., "--prevention", help="Prevention strategy."),
) -> None:
    """Add a reusable lesson."""
    def call() -> None:
        with open_context() as context:
            lesson = context.remember_lesson(category, problem, solution, prevention)
        _emit(f"Lesson added id={lesson.id} category={lesson.category!r}")

    _run_memory_call(call)


@lesson_app.command("list")
def lesson_list(
    limit: int = typer.Option(10, "--limit", "-n", min=1, help="Maximum rows."),
    category: str = typer.Option("", "--category", "-c", help="Optional category filter."),
) -> None:
    """List lessons."""
    def call() -> None:
        with open_context() as context:
            lessons = context.lessons(category or None, limit=limit)
        _print_lessons(lessons, "Lessons")

    _run_memory_call(call)


@command_app.command("add")
def command_add(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name."),
    shell: str = typer.Option(..., "--shell", help="Shell type."),
    command: str = typer.Option(..., "--command", help="Command text."),
    success: str = typer.Option(..., "--success", help="Whether the command succeeded: true or false."),
    error: str = typer.Option("", "--error", help="Error message if any."),
    correction: str = typer.Option("", "--correction", help="Correction applied if any."),
) -> None:
    """Add a command history row."""
    def call() -> None:
        success_flag = success.strip().lower() in {"1", "true", "yes", "y"}
        with open_context() as context:
            command_row = context.remember_command(
                agent_name=agent,
                shell_type=shell,
                command_text=command,
                success_flag=success_flag,
                error_message=error or None,
                correction_applied=correction or None,
            )
        _emit(f"Command added id={command_row.id} success={command_row.success_flag}")

    _run_memory_call(call)


@command_app.command("list")
def command_list(
    failed_only: bool = typer.Option(False, "--failed-only", help="Show failed commands only."),
    limit: int = typer.Option(10, "--limit", "-n", min=1, help="Maximum rows."),
) -> None:
    """List command history."""
    def call() -> None:
        with open_context() as context:
            commands = context.commands(limit=limit, success_flag=False if failed_only else None)
        _print_commands(commands, "Command history")

    _run_memory_call(call)


@snapshot_app.command("add")
def snapshot_add(
    title: str = typer.Option("", "--title", "-t", help="Snapshot title."),
    snapshot_type: str = typer.Option("manual", "--type", help="Snapshot type."),
    limit: int = typer.Option(100, "--limit", "-n", min=1, help="Maximum rows per memory collection."),
) -> None:
    """Create a sanitized memory snapshot."""
    def call() -> None:
        with open_context() as context:
            snapshot = context.remember_snapshot(
                snapshot_type=snapshot_type,
                title=title or None,
                limit=limit,
                tags={"source": "codex_memory.py"},
            )
        _emit(f"Snapshot added id={snapshot.id} type={snapshot.snapshot_type}")

    _run_memory_call(call)


@snapshot_app.command("list")
def snapshot_list(
    limit: int = typer.Option(10, "--limit", "-n", min=1, help="Maximum rows."),
) -> None:
    """List memory snapshots."""
    def call() -> None:
        with open_context() as context:
            snapshots = context.snapshots(limit=limit)
        _print_snapshots(snapshots, "Snapshots")

    _run_memory_call(call)


@snapshot_app.command("restore")
def snapshot_restore(
    snapshot_id: int = typer.Argument(..., help="Snapshot id to restore."),
) -> None:
    """Restore is intentionally blocked until backup/restore semantics are approved."""
    _emit(f"Snapshot restore is not enabled for id={snapshot_id}.")
    _emit("Create an explicit backup/restore plan before enabling destructive lifecycle operations.")
    raise typer.Exit(2)


@memory_app.command("compact")
def memory_compact() -> None:
    """Report compaction opportunities without deleting or rewriting memory."""
    def call() -> None:
        with open_context() as context:
            report = context.compact_memory()
        _section("Memory compaction report")
        _emit(f"Inactive decisions: {report.inactive_decisions}")
        _emit(f"Duplicate active decision issues: {len(report.duplicate_decision_keys)}")
        for issue in report.duplicate_decision_keys:
            _emit(f"- {_clip(issue, 180)}")
        _emit(report.suggested_action)

    _run_memory_call(call)


@contradictions_app.command("list")
def contradictions_list() -> None:
    """List detected memory contradictions."""
    def call() -> None:
        with open_context() as context:
            contradictions = context.contradictions()
        _section("Contradictions")
        for contradiction in contradictions:
            _emit(f"- {contradiction.kind}: ids={list(contradiction.ids)} {_clip(contradiction.message, 160)}")
        _emit(f"{len(contradictions)} contradiction(s).")

    _run_memory_call(call)


@orchestration_app.command("start")
def orchestrate_start(
    title: str = typer.Option(..., "--title", help="Orchestration title."),
    description: str = typer.Option(..., "--description", help="Orchestration description."),
    agent: str = typer.Option("orchestrator", "--agent", "-a", help="Assigned agent."),
) -> None:
    """Start a new orchestration execution."""
    def call() -> None:
        with open_context() as context:
            store = OrchestrationStore(context)
            execution = store.start_execution(title=title, description=description, assigned_agent=agent)
        _emit(f"Orchestration started execution_id={execution.execution_id} root_task_id={execution.root_task_id}")
        _emit(f"Title: {title}")
        _emit(f"Agent: {agent}")

    _run_memory_call(call)


@orchestration_app.command("phase")
def orchestrate_phase(
    execution_id: str = typer.Option(..., "--execution-id", help="Execution id."),
    title: str = typer.Option(..., "--title", help="Phase/task title."),
    agent: str = typer.Option("", "--agent", "-a", help="Assigned agent."),
    depends_on: str = typer.Option("", "--depends-on", help="Comma-separated task ids to depend on."),
    files: str = typer.Option("", "--files", help="Comma-separated files modified by this phase."),
) -> None:
    """Add a phase or subtask to an orchestration."""
    def call() -> None:
        with open_context() as context:
            store = OrchestrationStore(context)
            task_id = store.next_phase_id(execution_id)
            dependencies = tuple(d.strip() for d in depends_on.split(",") if d.strip()) if depends_on else ()
            file_list = tuple(f.strip() for f in files.split(",") if f.strip()) if files else ()
            store.record_task(
                task_id=task_id,
                execution_id=execution_id,
                dependencies=dependencies,
                files=file_list,
                status="pending",
            )
        _emit(f"Phase added task_id={task_id} execution_id={execution_id}")
        if dependencies:
            _emit(f"Depends on: {', '.join(dependencies)}")
        if file_list:
            _emit(f"Files: {', '.join(file_list)}")

    _run_memory_call(call)


@orchestration_app.command("validation")
def orchestrate_validation(
    execution_id: str = typer.Option(..., "--execution-id", help="Execution id."),
    task_id: str = typer.Option(..., "--task-id", help="Task id to validate."),
    command: str = typer.Option(..., "--command", help="Validation command."),
    status: str = typer.Option(..., "--status", help="Validation status: passed or failed."),
    output: str = typer.Option("", "--output", help="Validation output."),
) -> None:
    """Record a validation result for a task."""
    def call() -> None:
        with open_context() as context:
            store = OrchestrationStore(context)
            success = status.lower().strip() in {"passed", "success", "ok", "true", "1", "yes"}
            record = store.record_validation(task_id=task_id, command=command, success=success, output=output)
        _emit(f"Validation recorded task_id={task_id} command={_clip(command, 60)} success={record.success}")

    _run_memory_call(call)


@orchestration_app.command("conflict")
def orchestrate_conflict(
    execution_id: str = typer.Option(..., "--execution-id", help="Execution id."),
    description: str = typer.Option(..., "--description", help="Conflict description."),
    affected_tasks: str = typer.Option("", "--affected-tasks", help="Comma-separated task ids."),
) -> None:
    """Record a conflict in orchestration."""
    def call() -> None:
        with open_context() as context:
            store = OrchestrationStore(context)
            task_ids = tuple(t.strip() for t in affected_tasks.split(",") if t.strip()) if affected_tasks else ()
            conflicts = store.detect_conflicts(task_ids) if task_ids else []
        _emit(f"Conflict recorded execution_id={execution_id}")
        _emit(f"Description: {description}")
        if task_ids:
            _emit(f"Affected tasks: {', '.join(task_ids)}")
        _emit(f"Detected {len(conflicts)} conflict(s).")

    _run_memory_call(call)


@orchestration_app.command("status")
def orchestrate_status(
    execution_id: str = typer.Option(..., "--execution-id", help="Execution id."),
) -> None:
    """Show the status of an orchestration execution."""
    def call() -> None:
        with open_context() as context:
            store = OrchestrationStore(context)
            graph = store.get_task_graph(execution_id)
        _section(f"Orchestration status: {execution_id}")
        _emit(f"Total tasks: {len(graph.tasks)}")
        _section("Tasks")
        for task in graph.tasks:
            deps = f" <- {', '.join(task.dependencies)}" if task.dependencies else ""
            _emit(f"- {task.task_id} [{task.status}]{deps}")
        _section("Task summary")
        completion = tuple(t for t in graph.tasks if t.status == "done")
        blocked = tuple(t for t in graph.tasks if t.status == "blocked")
        pending = tuple(t for t in graph.tasks if t.status == "pending")
        _emit(f"Done: {len(completion)}/{len(graph.tasks)}")
        _emit(f"Blocked: {len(blocked)}/{len(graph.tasks)}")
        _emit(f"Pending: {len(pending)}/{len(graph.tasks)}")

    _run_memory_call(call)


@orchestration_app.command("finish")
def orchestrate_finish(
    execution_id: str = typer.Option(..., "--execution-id", help="Execution id."),
    summary: str = typer.Option(..., "--summary", help="Completion summary."),
    status: str = typer.Option("done", "--status", "-s", help="Final status: done or blocked."),
) -> None:
    """Finalize and consolidate an orchestration execution."""
    def call() -> None:
        with open_context() as context:
            store = OrchestrationStore(context)
            graph = store.get_task_graph(execution_id)
            task_ids = tuple(task.task_id for task in graph.tasks)
            result = store.consolidate_tasks(task_ids)
            store.finish_execution(execution_id, summary=summary, status=status)
        _section(f"Orchestration completion: {execution_id}")
        _emit(f"Summary: {summary}")
        _emit(f"Status: {status}")
        _emit(f"Total tasks: {result.total}")
        _emit(f"Completed: {result.completed}/{result.total}")
        _emit(f"Pending: {result.pending}/{result.total}")
        _emit(f"Blocked: {result.blocked}/{result.total}")

    _run_memory_call(call)


if __name__ == "__main__":
    app()
