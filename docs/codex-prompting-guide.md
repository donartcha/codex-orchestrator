# Codex Prompting Guide: Resilient Local Orchestration

This document extends the root `README.md` with runtime-aware prompting patterns for the local Codex system.

## Goal

Prompt Codex to behave like a resilient agentic runtime:

- resolve Python before context tooling
- validate runtime before complex work
- use fallback when the intended path cannot work
- use recovery when the path can be corrected
- record reusable lessons in MariaDB
- degrade safely to `.codex/context/*.md` only when MariaDB is unavailable

## Runtime Bootstrap Prompt

```text
$context-recovery

Before work, validate the runtime:

Set-Location .codex\context-api
python codex_memory.py resolve-python
python codex_memory.py runtime-check
python codex_memory.py bootstrap --limit 5

Report active interpreter, active shell, fallback status, environment warnings,
pending tasks, recent decisions, lessons and failed commands.
```

## Environment-Aware Implementation Prompt

```text
$orchestrator $implementation $testing $reviewing

Goal:
<goal>

Runtime:
Resolve Python first. Prefer `.codex/context-api/.venv/Scripts/python.exe`.
Validate `typer`, `sqlalchemy` and `pymysql`. Use fallback if global Python is
missing required imports.

Memory:
Bootstrap with `codex_memory.py bootstrap --limit 5`. If MariaDB is unavailable,
use `.codex/context/*.md` temporarily and record a warning later.

Execution:
Use PowerShell. Do not run destructive commands. Keep edits inside <scope>.

Validation:
Run focused checks and `python codex_memory.py env-status`.

Finish:
Record task logs and reusable lessons when appropriate.
```

## Recovery vs Fallback

Recovery corrects the failing path.

```text
bash command invalid in PowerShell
->
convert to PowerShell
->
validate quoting
->
retry safely
```

Fallback selects a different path.

```text
global python missing typer
->
use workspace .venv python
```

Use recovery for syntax, quoting, paths and command shape. Use fallback for missing dependencies, unavailable services and incompatible interpreters.

## Official Fallback Chains

Python:

```text
global python fails
->
local .venv python
->
poetry
->
uv
->
pyenv
->
system python
```

MariaDB:

```text
MariaDB unavailable
->
use .codex/context/*.md temporarily
->
register warning
->
retry later
```

PowerShell:

```text
bash syntax detected
->
convert to PowerShell
->
validate quoting
->
retry safely
```

Command recovery:

```text
command fails
->
analyze error
->
search lessons
->
search command history
->
generate corrected command
->
retry if safe
```

## CLI Commands

```powershell
Set-Location .codex\context-api
python codex_memory.py resolve-python
python codex_memory.py runtime-check
python codex_memory.py env-status
python codex_memory.py bootstrap --limit 5
```

If global Python lacks dependencies:

```powershell
.\.venv\Scripts\python.exe codex_memory.py resolve-python
.\.venv\Scripts\python.exe codex_memory.py runtime-check
.\.venv\Scripts\python.exe codex_memory.py bootstrap --limit 5
```

## Lessons Policy

Store a lesson when the result is reusable:

```text
Missing typer in global python
->
Fallback to local venv python succeeded
->
Store python-environment lesson
```

Do not store secrets, full `.env` files or one-off noise.

Use task logs for task-specific summaries. Use lessons for repeatable future guidance.

## Validation Checklist

- `python -m py_compile codex_memory.py`
- `python scripts/resolve_python_env.py`
- `python scripts/runtime_validation.py`
- `python codex_memory.py runtime-check`
- `python codex_memory.py resolve-python`
- `python codex_memory.py env-status`
- `python codex_memory.py bootstrap --limit 3`

The expected healthy state can still be `WARNING` when the warning is honest and non-blocking, such as global Python missing optional context dependencies while workspace `.venv` is valid.
