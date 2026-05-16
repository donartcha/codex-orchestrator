# Codex Context API

Local layer for storing persistent Codex memory through a single facade with transparent fallback.

## Purpose

This directory keeps durable context so Codex can recover tasks, decisions, task logs, commands, lessons and orchestration records without relying only on conversation history.

The official source for agents, skills and CLIs is `open_context()` or `codex_memory.py`. MariaDB is the primary backend; SQLite and JSON/Markdown are internal emergency fallbacks.

## Architecture

- `codex_context/models.py`: SQLAlchemy models and tables.
- `codex_context/repositories.py`: internal persistence operations.
- `codex_context/context.py`: official facade for agents, skills and CLIs.
- `codex_context/fallback.py`: internal backend selection.
- `codex_context/backends/`: MariaDB, SQLite and file backends.
- `codex_memory.py`: unified official CLI.
- `scripts/*.py`: compatible legacy scripts.

Agent, skill and CLI code must use:

```python
from codex_context.context import open_context
```

Do not open SQLAlchemy sessions or MariaDB/SQLite connections directly outside the internal layer. Agents and skills do not choose the backend.

## MariaDB And `.env`

MariaDB is tried first. If it is unavailable, `open_context()` uses SQLite. If SQLite is also unavailable, it uses the JSON/Markdown fallback. Fallback emits a warning, but agent and skill code does not catch or implement that decision.

Activate the virtual environment from PowerShell:

```powershell
cd .codex/context-api
.\.venv\Scripts\Activate.ps1
```

Install dependencies if needed:

```powershell
pip install -r requirements.txt
```

Configure `.env` from the example:

```powershell
copy .env.example .env
```

Do not print or store real passwords in docs, logs, memory or responses.

Initialize tables only when needed:

```powershell
python scripts/init_db.py
```

`init_db.py` creates tables if they do not exist. It does not run destructive migrations.

## Official CLI

Use `codex_memory.py` as the single entrypoint:

```powershell
python codex_memory.py check
python codex_memory.py resolve-python
python codex_memory.py runtime-check
python codex_memory.py env-status
python codex_memory.py backend-status
python codex_memory.py bootstrap --limit 5
python codex_memory.py finish --task-id 1 --summary "Summary of completed work" --status done
python codex_memory.py status
```

Lifecycle commands added by the harness evolution work:

```powershell
python codex_memory.py snapshot add --title "pre-change" --limit 100
python codex_memory.py snapshot list --limit 10
python codex_memory.py decision supersede <old_id> <new_id>
python codex_memory.py memory compact
python codex_memory.py contradictions list
```

`snapshot restore` is intentionally blocked until backup and dry-run restore semantics are approved.

Orchestration commands also use the same facade and backend chain:

```powershell
python codex_memory.py orchestrate start --title "Feature work" --description "Coordinate implementation and validation."
python codex_memory.py orchestrate phase --execution-id exec-0001 --title "Implementation" --agent implementation-agent
python codex_memory.py orchestrate status --execution-id exec-0001
```

Structured orchestration was initially prototyped as JSON files under `.codex/context-api/orchestration`. That path is legacy runtime output, not a separate architecture. Current orchestration persistence goes through `open_context()` and then MariaDB, SQLite fallback or file emergency fallback. Legacy JSON orchestration directories are ignored by Git.

## Python Environment Resolution

The CLI can resolve the correct interpreter before running context tools.

Priority:

```text
.venv/Scripts/python.exe
->
Poetry environment
->
uv-managed Python
->
pyenv
->
system Python
```

Command:

```powershell
python codex_memory.py resolve-python
```

The resolver detects the active virtualenv, validates minimum imports (`typer`, `sqlalchemy`, `pymysql`), reports broken imports and shows warnings. It does not install dependencies, modify the global `PATH` or touch `.env`.

If global Python does not have the required dependencies, use the local interpreter:

```powershell
.\.venv\Scripts\python.exe codex_memory.py bootstrap --limit 5
```

## Runtime Validation

Full validation:

```powershell
python codex_memory.py runtime-check
python codex_memory.py env-status
```

It validates:

- Python interpreter
- virtualenv
- PowerShell
- active memory backend
- required imports
- `codex_memory.py` availability
- filesystem permissions
- UTF-8 compatibility
- shell compatibility

Possible statuses:

- `OK`
- `WARNING`
- `ERROR`
- `FALLBACK_USED`

## Recovery Vs Fallback

Recovery corrects the problem and retries the original path.

```text
bash command invalid in PowerShell
->
convert command
->
retry safely
```

Fallback uses an alternate path.

```text
global python fails
->
use local .venv python
```

Recovery and fallback are complementary.

## Transparent Backend Fallback

MariaDB is the primary backend. If MariaDB fails, the context layer selects SQLite. If SQLite fails, it selects the JSON/Markdown file fallback. This happens inside `.codex/context-api`.

```text
MariaDB unavailable
->
SQLite fallback
-> if SQLite unavailable
JSON/Markdown file fallback
->
show warning
```

Agents and skills must keep using exactly the same interface:

```python
from codex_context.context import open_context
```

They can also inspect status without controlling the backend:

```powershell
python codex_memory.py backend-status
```

Correct usage:

- Use `open_context()`.
- Use `python codex_memory.py ...`.
- Report backend status if relevant.

Incorrect usage:

- Connect directly to MariaDB.
- Connect directly to SQLite.
- Implement fallback logic inside prompts, `AGENT.md` or `SKILL.md`.
- Duplicate persistence logic.

### Tasks

Tasks represent pending, in-progress or completed work.

```powershell
python codex_memory.py task add --title "Review API" --description "Validate memory CLI" --agent codex --priority high
python codex_memory.py task list --status pending --limit 20
python codex_memory.py task status --task-id 1 --status done
```

### Task Logs

Task logs record what happened in a specific task. They are not lessons.

```powershell
python codex_memory.py task log --task-id 1 --content "Validation completed" --agent codex --type validation
python codex_memory.py task logs --task-id 1 --limit 10
```

### Decisions

Decisions store technical or architectural decisions.

```powershell
python codex_memory.py decision add --key "memory-cli" --title "Single CLI" --rationale "Centralizes context input and output"
python codex_memory.py decision list --limit 10
```

### Lessons

Lessons store reusable learning for future work.

```powershell
python codex_memory.py lesson add --category "powershell" --problem "Bash command used in PowerShell" --solution "Use native cmdlets" --prevention "Check shell before execution"
python codex_memory.py lesson list --limit 10
```

### Commands

Commands store execution history, errors and corrections.

```powershell
python codex_memory.py command add --agent powershell-agent --shell powershell --command "python codex_memory.py check" --success true
python codex_memory.py command list --failed-only --limit 10
```

## Conceptual Differences

- `tasks`: work that should be done or has already been done.
- `task_logs`: what happened in a specific task.
- `decisions`: technical or architectural decisions.
- `lessons`: reusable learning that prevents future errors.
- `commands`: terminal execution history, including errors and corrections.

## Recommended Workflow Before Work

```powershell
cd .codex/context-api
.\.venv\Scripts\Activate.ps1
python codex_memory.py bootstrap --limit 5
```

## Recommended Workflow After Work

```powershell
python codex_memory.py finish --task-id 1 --summary "Summary of completed work" --status done
```

Show overall status:

```powershell
python codex_memory.py status
```

## Python Usage

```python
from codex_context.context import open_context

with open_context() as context:
    task = context.remember_task(
        title="Review local memory",
        description="Store a task through the unified API.",
        assigned_agent="codex",
        priority="normal",
    )
    context.remember_task_log(
        task_id=task.id,
        content="Summary of what happened in the task.",
        agent_name="codex",
        log_type="summary",
    )
    context.remember_command(
        agent_name="codex",
        shell_type="powershell",
        command_text="python codex_memory.py check",
        success_flag=True,
    )
    pending = context.tasks(status="pending", limit=5)
```

The public context facade is explicit. Use:

```python
from codex_context.context import open_context, validate_facade_usage

report = validate_facade_usage()
assert report.ok
```

Deprecated compatibility remains for direct `Engine`, `Session`, `CodexContext.engine` and `CodexContext.session()` access, but those paths emit `DeprecationWarning` and should not be used by agents, skills or CLIs.

Backend implementations must satisfy the shared contract in `codex_context.backends.contract`. Local parity tests cover SQLite and file fallback without touching real memory. The contract includes orchestration executions, tasks, validations and conflicts so orchestration does not choose a separate storage path.

Memory writes through `CodexContext` are sanitized before backend persistence. Redaction is irreversible; reports contain metadata only and never preserve original secrets.

Additional recovery/fallback helpers:

```python
from codex_context.context import open_context

with open_context() as context:
    context.remember_recovery_lesson(
        category="python-environment",
        problem_description="Global Python could not import typer.",
        solution_description="Fallback to workspace .venv Python.",
        prevention_strategy="Run resolve-python before Codex context tooling.",
    )
    context.remember_fallback_event(
        agent_name="codex_memory",
        shell_type="powershell",
        command_text="python codex_memory.py bootstrap --limit 5",
        fallback_from="C:\\Python313\\python.exe",
        fallback_to=".\\.venv\\Scripts\\python.exe",
        reason="missing typer",
    )
```

## Security Policy

- Do not store secrets.
- Do not print passwords.
- Do not dump `.env`.
- Do not record tokens in `commands`, `task_logs`, `lessons` or `decisions`.
- Recover only recent and relevant context.
- Use `open_context()` for persistent memory.

## Legacy Scripts

These scripts are kept for compatibility, but they are not the first option:

- `scripts/check_connection.py`
- `scripts/context_bootstrap.py`
- `scripts/context_finish.py`
- `scripts/add_task.py`
- `scripts/list_tasks.py`
- `scripts/update_task_status.py`
- `scripts/add_decision.py`
- `scripts/list_decisions.py`
- `scripts/add_lesson.py`
- `scripts/list_lessons.py`
- `scripts/add_command_log.py`
- `scripts/list_command_history.py`

Use `python codex_memory.py ...` as the official CLI.

Legacy scripts have compatibility tests. Some use older positional argument contracts; preserve those contracts until a dedicated CLI refactor migrates callers safely.

## Tests

Run the local executable suite:

```powershell
cd .codex/context-api
.\.venv\Scripts\python.exe -m pytest tests -v
```

The suite uses temporary SQLite/file backends and disables MariaDB for write-oriented CLI tests. MariaDB checks are integration-only unless a safe service is explicitly provisioned.

Markers include:

- `fallback`
- `parity`
- `cli`
- `powershell`
- `sanitization`
- `lifecycle`
- `orchestration`
- `hooks`
- `integration`

## Tables

`init_db.py` creates these tables if they do not exist:

- `context_snapshots`
- `architectural_decisions`
- `tasks`
- `task_logs`
- `orchestration_executions`
- `orchestration_tasks`
- `orchestration_validations`
- `orchestration_conflicts`
- `command_history`
- `lessons_learned`
- `project_constraints`
- `context_embeddings`
- `agent_memory`
- `file_index`
