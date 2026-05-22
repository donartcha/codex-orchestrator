# Context API Memory Policy

Persistent memory is accessed only through `.codex/context-api/codex_context/context.py`:

```python
from codex_context.context import open_context
```

Backend selection is transparent inside `.codex/context-api`: MariaDB primary, SQLite fallback, JSON/Markdown emergency fallback. Agents do not choose backends and should use `backend-status` only for diagnostics.

If the facade lacks a needed method, document the gap and propose a clean extension.

## Lessons

Reusable lessons must be persisted with the lesson interface:

```powershell
python codex_memory.py lesson add --category "category" --problem "Repeatable problem" --solution "Correction" --prevention "Prevention strategy"
python codex_memory.py lesson add --task-id 1 --category "category" --problem "Task-specific repeatable problem" --solution "Correction" --prevention "Prevention strategy"
python codex_memory.py lesson list --category "category" --limit 10
python codex_memory.py lesson list --task-id 1 --limit 10
```

Or through the facade:

```python
context.remember_lesson("category", "Repeatable problem", "Correction", "Prevention strategy")
context.remember_lesson("category", "Task-specific repeatable problem", "Correction", "Prevention strategy", task_id=1)
```

Lessons, decisions, commands and snapshots can be global or task-associated through nullable `task_id`. Use task scope for provenance and task-specific retrieval; leave reusable project-wide records global.

Do not use `finish` as a substitute for lessons. `finish` records task logs and optional task status only.
