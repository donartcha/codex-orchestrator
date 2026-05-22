# Compaction Policy

- Compact only stale or repetitive context.
- Keep recent decisions and unresolved tasks accessible.
- Propose snapshots when context grows beyond useful working memory.
- Use `.codex/context-api` through `open_context()` and propose `context.py` extensions for missing operations.
- During compaction, promote repeated recoveries or fallback patterns into lessons with `codex_memory.py lesson add`; keep one-off task narration as task logs.
- Preserve task-associated `task_id` on decisions, commands, lessons and snapshots when compacting or summarizing provenance.
