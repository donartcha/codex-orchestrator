# Codex entrypoint

Before doing any work, read:

- `.codex/AGENTS.md`
- relevant `.codex/agents/*/AGENT.md`
- relevant `.codex/skills/*/SKILL.md`

Persistent context is managed through:

- `.codex/context-api/codex_context/context.py`
- `.codex/context-api/codex_memory.py`

Use:

```python
from codex_context.context import open_context
```

For complex tasks, use subagents explicitly and let the orchestrator assign the best agent for each part.

Use `python codex_memory.py bootstrap` before substantial work and `python codex_memory.py finish` after substantial work to keep memory current through the official context API.

## Environment resolution policy

Before substantial Python-based work, resolve the runtime environment:

```powershell
cd .codex/context-api
python codex_memory.py resolve-python
python codex_memory.py runtime-check
```

Prefer the workspace-local `.codex/context-api/.venv/Scripts/python.exe` when global Python lacks required imports.

## Runtime validation policy

Use `python codex_memory.py runtime-check` to validate Python, PowerShell, the active memory backend, required imports, filesystem permissions, UTF-8 compatibility and shell compatibility.

## Fallback strategy policy

Fallback is using an alternate path. Recovery is correcting the failing path. They are complementary.

Examples:

```text
global python fails -> local .venv python
bash syntax fails -> convert to PowerShell and retry safely
MariaDB unavailable -> context API selects SQLite, then JSON/Markdown file fallback
```

## Bootstrap validation workflow

Bootstrap should show memory plus runtime context:

```powershell
python codex_memory.py bootstrap --limit 5
```

The bootstrap output should include pending tasks, decisions, lessons, failed commands, environment warnings, active interpreter, active shell and backend fallback status.

Agents and skills never choose MariaDB, SQLite or file storage manually. Always use `open_context()` or `python codex_memory.py ...`; backend selection and error handling are internal to `.codex/context-api`.

## Safe recovery workflow

When a command fails:

1. Capture exact error text.
2. Search relevant lessons and command history.
3. Decide whether recovery or fallback is appropriate.
4. Retry only when safe.
5. Record reusable lessons without storing secrets.
