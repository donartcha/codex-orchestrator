# Summarization Rules

- Preserve decisions, constraints, task status, owners, risks and next steps.
- Remove duplicate narration and transient command noise.
- Mark uncertainty clearly.
- Treat the official context API as source of truth and `.codex/context/` as a human mirror or emergency file fallback.
- Use `.codex/context-api` through `open_context()` for persisted context.
- Store reusable learning as lessons, not summaries: use `codex_memory.py lesson add` or `context.remember_lesson()` when the note has a repeatable problem, correction and prevention strategy.
- Add nullable `task_id` to lessons, decisions, commands or snapshots when the record should remain tied to a specific task; leave it empty for global context.
- Use task logs for current-task narrative, validation notes and handoffs.
