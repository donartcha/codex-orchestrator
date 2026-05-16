# Codex Local Agent System

This document is the root coordination policy for local Codex work in this workspace.

## Workspace Profile

- Stack detected: Python local context API, transparent MariaDB/SQLite/file backend fallback, SQLAlchemy models/repositories, Codex skills and agent Markdown definitions.
- Shell: PowerShell.
- OS: Windows.
- Tools detected: Python virtual environment in `.codex/context-api/.venv`, context memory CLI, `rg`, Git, PowerShell cmdlets.
- Valid commands:
  - `cd .codex/context-api`
  - `.\.venv\Scripts\Activate.ps1`
  - `python codex_memory.py check`
  - `python codex_memory.py bootstrap --limit 5`
  - `python codex_memory.py finish --task-id 1 --summary "What changed" --status done`
  - `python codex_memory.py task list --status pending --limit 20`
  - `python codex_memory.py command list --failed-only --limit 10`
- Legacy commands:
  - `python scripts/check_connection.py`
  - `python scripts/context_bootstrap.py`
  - `python scripts/context_finish.py`
  - other `scripts/*.py` helpers
- Commands pending validation:
  - none

## Environment Resolution Policy

Python-based Codex tooling must resolve the interpreter before substantial work.

Priority order:

```text
.codex/context-api/.venv/Scripts/python.exe
->
Poetry environment
->
uv-managed Python
->
pyenv
->
system Python
```

The resolver must detect the active virtualenv, validate required imports and report warnings. It must not install dependencies, modify global `PATH` or edit `.env`.

Official commands:

```powershell
cd .codex/context-api
python codex_memory.py resolve-python
python codex_memory.py env-status
```

Prefer the workspace-local interpreter when global Python cannot import `typer`, `sqlalchemy` or `pymysql`.

## Runtime Validation Policy

Before complex or long-running work, validate:

- Python interpreter
- virtualenv
- PowerShell
- active memory backend
- required imports
- `codex_memory.py` availability
- filesystem permissions
- UTF-8 compatibility
- shell compatibility

Use:

```powershell
python codex_memory.py runtime-check
```

Runtime status values are `OK`, `WARNING`, `ERROR` and `FALLBACK_USED`.

## Fallback Strategy Policy

Fallback means using an alternate path when the intended path cannot work. Recovery means correcting the failing path and retrying it.

Official strategy details live in `.codex/agents/shared/fallback-strategies.md`.

Examples:

```text
global python fails -> local .venv python
MariaDB unavailable -> context API selects SQLite, then JSON/Markdown file fallback
bash syntax detected -> convert to PowerShell and retry safely
```

Important fallbacks should be recorded as command history and reusable lessons through `open_context()` when any writable backend is available.

## Bootstrap Validation Workflow

`python codex_memory.py bootstrap --limit 5` should resolve Python, validate runtime and then retrieve memory.

Bootstrap output should include:

- pending tasks
- recent decisions
- recent lessons
- failed commands
- environment warnings
- active interpreter
- active shell
- fallback status

If MariaDB fails, `open_context()` should degrade to SQLite, then JSON/Markdown file fallback, emit a warning and keep the CLI working.

## Safe Recovery Workflow

When a command or workflow fails:

1. Capture exact error text.
2. Search relevant lessons.
3. Search command history.
4. Decide whether recovery or fallback is appropriate.
5. Generate the smallest safe correction.
6. Retry only if safe.
7. Store reusable lessons and command corrections.

## Persistent Memory Policy

Persistent memory is accessed through `.codex/context-api/`. MariaDB is primary, SQLite is the first fallback and JSON/Markdown files are the emergency fallback.

Mandatory Python access:

```python
from codex_context.context import open_context
```

Mandatory terminal access:

```powershell
python codex_memory.py ...
```

Rules:

- Before work, retrieve relevant context.
- During work, record important commands, decisions, errors, corrections and task changes.
- After work, record task logs, lessons, follow-ups and task status.
- Do not store secrets, tokens, passwords or full `.env` contents.
- Do not print passwords.
- Do not query the entire database without a relevant reason.
- Retrieve recent and relevant context only.
- Use `.codex/context/` Markdown files as a human-readable mirror and emergency file fallback, not as an agent-selected backend.
- If MariaDB is unavailable, continue using `open_context()` or `codex_memory.py`; the context API selects SQLite or file fallback internally.

Direct SQLAlchemy sessions, repositories, models or backend-specific connections are not the official agent interface. Use internal layers only when changing the context API itself, document the reason, propose a clean `context.py` extension and avoid duplicating logic.

Backend policy:

- Correct: use `open_context()`.
- Correct: use `python codex_memory.py ...`.
- Correct: report `context.backend_status()` or `python codex_memory.py backend-status` when relevant.
- Incorrect: connect directly to MariaDB.
- Incorrect: connect directly to SQLite.
- Incorrect: implement fallback logic inside prompts, `AGENT.md` or `SKILL.md`.
- Incorrect: duplicate persistence logic outside `.codex/context-api`.

## Mandatory Execution Workflow

```text
memory bootstrap
->
context check
->
planning
->
task decomposition
->
agent assignment
->
implementation
->
validation
->
review
->
fix
->
revalidation
->
memory update
->
summary
```

## Memory Bootstrap

Before starting a task:

1. Activate the virtual environment when needed:

```powershell
cd .codex/context-api
.\.venv\Scripts\Activate.ps1
```

2. Retrieve relevant pending tasks, recent decisions, relevant lessons and recent failed commands:

```powershell
python codex_memory.py bootstrap --limit 5
```

3. Check connection separately when needed:

```powershell
python codex_memory.py check
```

Or use the API:

```python
from codex_context.context import open_context

with open_context() as context:
    pending = context.tasks("pending", limit=5)
    decisions = context.decisions(limit=5)
    lessons = context.lessons(limit=5)
    failed_commands = context.commands(limit=5, success_flag=False)
```

## Memory Update

At the end of work:

- Update task status.
- Record relevant decisions.
- Record commands executed.
- Record errors and corrections.
- Record reusable lessons.
- Record task logs for task-specific summaries.
- Record follow-up tasks.

Preferred finish command:

```powershell
python codex_memory.py finish --task-id 1 --summary "What changed" --status done
```

Task summaries must be stored as `task_logs`. Lessons are only for reusable future learning.

## Coordination Rules

- Use `orchestrator` for complex, multi-file or multi-agent work.
- Use `context-manager` when relevance, summarization, compaction or contradictions matter.
- Use `implementation-agent` for scoped changes.
- Use `reviewer-agent` for code review, regressions and risks.
- Use `testing-agent` for test strategy, execution and coverage follow-ups.
- Use `debugging-agent` for root cause analysis and repeated failures.
- Use `documentation-agent` for durable docs and handovers.
- Use `powershell-agent` for Windows shell execution and recovery.
- Avoid duplicate tasks and decisions by checking memory first.
- When agents disagree, prefer documented constraints, recent decisions and validated evidence. Record the resolution.
- Escalate blockers to the orchestrator with exact error, attempted fixes and affected files.

## Subagent Rules

- For complex tasks, use `orchestrator` as the main agent.
- Launch specialized subagents when parallel work adds value or the user asks for it.
- Each subagent returns summary, risks, affected files and validations.
- The orchestrator consolidates results and updates memory.
- No subagent modifies outside its assigned scope.
- Shared context must be recovered through `open_context()`.

## PowerShell Execution Policy

- PowerShell is the primary shell.
- Prefer native cmdlets.
- Avoid Bash unless explicitly needed.
- Validate quoting, encoding and Windows paths.
- Detect dangerous commands before execution.
- Record important commands with `python codex_memory.py command add ...` or `remember_command()`.
- Analyze and correct errors before retrying.
- Consult previous lessons before retrying repeatable failures.

## Safety Policy

- Do not store secrets.
- Do not print passwords.
- Do not execute destructive commands without confirmation.
- Do not modify real `.env` files unless explicitly requested.
- Do not delete files without confirmation.
- Do not modify unrelated files.
- Do not record sensitive content in memory backends.

## Legacy Scripts

The old `.codex/context-api/scripts/*.py` commands are kept for compatibility. They are legacy/wrappers and should not be the first option. Prefer `python codex_memory.py ...`.
