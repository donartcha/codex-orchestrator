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

## Memory & Context Policy

Persistent memory, context retrieval, fallback strategies, and memory updates MUST follow the official API.
Read .codex/API.md for exact python codex_memory.py ... commands, Python facade instructions (open_context()), and database fallbacks.

Agents must NOT duplicate database connection logic and MUST use .codex/API.md as the sole source of truth for context operations.

## Coordination Rules

- Use `orchestrator` for complex, multi-file or multi-agent work.
- Use `context-manager` when relevance, summarization, compaction or contradictions matter.
- Use `implementation-agent` for scoped changes.
- Use `reviewer-agent` for code review, regressions and risks.
- Use `testing-agent` for test strategy, execution and coverage follow-ups.
- Use `debugging-agent` for root cause analysis and repeated failures.
- Use `git-agent` for Git synchronization, remotes, commits, GPG signing recovery and nested repository state.
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
