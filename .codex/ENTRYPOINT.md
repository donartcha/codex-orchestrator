# Codex Entrypoint

This file is mandatory for all Codex operations in this workspace.

## Required reading order

1. `AGENTS.md`
2. `.codex/ENTRYPOINT.md`
3. Relevant `.codex/policies/*.md`
4. Relevant `.codex/agents/*/AGENT.md`
5. Relevant `.codex/skills/*/SKILL.md`
6. `.codex/API.md` when memory, context, fallback status or CLI persistence is involved

## Official context API

```python
from codex_context.context import open_context
```

## Official CLI commands

```powershell
cd .codex/context-api
.\.venv\Scripts\python.exe codex_memory.py bootstrap --mode new-task --title "Brief task title" --limit 5
.\.venv\Scripts\python.exe codex_memory.py runtime-check
```

## Backend access prohibition

Do not access any backend directly.

- no direct MariaDB access
- no direct SQLite access
- no direct JSON/Markdown fallback manipulation
- no direct ORM/session access

Use the official context API and CLI only.

## Orchestration and subagents

Use subagents when the user explicitly requests orchestration, or for complex, cross-domain, multi-file or multi-agent tasks.

## Finish command

```powershell
.\.venv\Scripts\python.exe codex_memory.py finish
```

## Additional policies

Read the policy modules under `.codex/policies/` for runtime, fallback, recovery, validation, and orchestration rules.
