# Local Agent System

This document is the root coordination policy for local work in this workspace.

## Entry point and policy reference

Read these first:

- `.codex/ENTRYPOINT.md`
- `.codex/policies/runtime-policy.md`
- `.codex/policies/fallback-policy.md`
- `.codex/policies/recovery-policy.md`
- `.codex/policies/validation-policy.md`
- `.codex/policies/orchestration-policy.md`

Then read the relevant `.codex/agents/*/AGENT.md` and `.codex/skills/*/SKILL.md` files for the task. Read `.codex/API.md` whenever memory, context, fallback status or CLI persistence is involved.

## Workspace Profile

- Stack detected: Python local context API, transparent MariaDB/SQLite/file backend fallback, SQLAlchemy models/repositories, Codex skills and agent Markdown definitions.
- Shell: PowerShell.
- OS: Windows.
- Tools detected: Python virtual environment in `.codex/context-api/.venv`, context memory CLI, `rg`, Git, PowerShell cmdlets.
- Valid commands:
  - `cd .codex/context-api`
  - `.\.venv\Scripts\Activate.ps1`
  - `.\.venv\Scripts\python.exe codex_memory.py check`
  - `.\.venv\Scripts\python.exe codex_memory.py bootstrap --mode new-task --title "Brief task title" --limit 5`
  - `.\.venv\Scripts\python.exe codex_memory.py finish --task-id 1 --summary "What changed" --status done`
  - `.\.venv\Scripts\python.exe codex_memory.py task list --status pending --limit 20`
  - `.\.venv\Scripts\python.exe codex_memory.py command list --failed-only --limit 10`
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
.\.venv\Scripts\python.exe codex_memory.py resolve-python
.\.venv\Scripts\python.exe codex_memory.py env-status
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
.\.venv\Scripts\python.exe codex_memory.py runtime-check
```

Runtime status values are `OK`, `WARNING`, `ERROR` and `FALLBACK_USED`.

`WARNING` permits continuing when the warning does not affect the task. Record relevant warnings in memory during finish or command history. Ask the user before continuing only when a warning can change task behavior, data safety or validation trust.

## Memory & Context Policy

Persistent memory, context retrieval, fallback strategies, and memory updates MUST follow the official API.
Read .codex/API.md for exact `.\.venv\Scripts\python.exe codex_memory.py ...` commands, Python facade instructions (open_context()), and database fallbacks.

Agents must NOT duplicate database connection logic and MUST use .codex/API.md as the sole source of truth for context operations.

## Coordination Rules

- Use `orchestrator` when the user explicitly requests orchestration, or for complex, cross-domain, multi-file or multi-agent work.
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

- For complex tasks or explicit orchestration requests, use `orchestrator` as the main agent.
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
- Record important commands with `.\.venv\Scripts\python.exe codex_memory.py command add ...` or `remember_command()`.
- Analyze and correct errors before retrying.
- Consult previous lessons before retrying repeatable failures.

## File Encoding Policy

- Preserve existing file encoding when reading files.
- New and modified text files should be written as UTF-8 without BOM unless the file already uses another encoding for a documented reason.
- Do not introduce BOM markers.
- For PowerShell writes, prefer APIs or commands that explicitly write UTF-8 without BOM.
- If encoding is uncertain for a critical file, inspect it before editing.

## Safety Policy

- Do not store secrets.
- Do not print passwords.
- Do not execute destructive commands without confirmation.
- Do not modify real `.env` files unless explicitly requested.
- Do not delete files without confirmation.
- Do not modify unrelated files.
- Do not record sensitive content in memory backends.

## Legacy Scripts

The old `.codex/context-api/scripts/*.py` commands are kept for compatibility. They are legacy/wrappers and should not be the first option. Prefer `.\.venv\Scripts\python.exe codex_memory.py ...`.

## Standard Work Loop

1. Read `AGENTS.md` and `.codex/ENTRYPOINT.md`.
2. Read relevant policies.
3. Resolve Python and run `runtime-check` when work is substantial.
4. Bootstrap memory with a task title.
5. Work within scope.
6. Validate with task-appropriate checks.
7. Record `finish`, command history or reusable lessons when relevant.
