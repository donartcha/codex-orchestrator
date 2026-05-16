# Fallback Strategies

These strategies define official recovery and fallback behavior for local Codex orchestration.

## Recovery vs Fallback

Recovery corrects the immediate problem and retries the intended path.

```text
bash command invalid in PowerShell
->
convert command
->
validate quoting
->
retry safely
```

Fallback uses an alternate path when the intended path cannot work.

```text
global python fails
->
use local .venv python
```

Recovery and fallback are complementary. Prefer recovery when the original path can be safely corrected. Prefer fallback when the original path lacks required runtime support.

## Python fallback

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

Rules:

- Prefer `.codex/context-api/.venv/Scripts/python.exe` when available and complete.
- Detect the active virtualenv, but do not assume it is correct.
- Validate `typer`, `sqlalchemy` and `pymysql` before running context tooling.
- Do not install dependencies automatically.
- Do not modify global `PATH`.
- Record a lesson when a fallback pattern is reusable.

## Memory backend fallback

```text
MariaDB unavailable
->
open_context() selects SQLite fallback
-> if SQLite unavailable
open_context() selects JSON/Markdown file fallback
->
register warning
->
retry later
```

Rules:

- MariaDB remains the primary backend, but agents do not select backends.
- Agents and skills always use `open_context()` or `python codex_memory.py ...`.
- Do not connect directly to MariaDB or SQLite.
- Do not implement fallback logic in prompts, `AGENT.md` or `SKILL.md`.
- Use `context.backend_status()` or `python codex_memory.py backend-status` only to report diagnostics.

## PowerShell fallback

```text
bash syntax detected
->
convert to PowerShell
->
validate quoting
->
retry safely
```

Rules:

- Prefer native PowerShell cmdlets.
- Validate paths with `-LiteralPath` when possible.
- Ask before destructive commands.
- Record failed and corrected command pairs when useful.

## Command recovery

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

Rules:

- Do not blindly retry.
- Use exact error text.
- Consult memory for repeated patterns.
- Store reusable lessons, not one-off noise.
