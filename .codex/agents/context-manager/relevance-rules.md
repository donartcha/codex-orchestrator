# Relevance Rules

- Retrieve context linked to the current task, touched files, agent role or repeated error.
- Prefer `task_id` filters for task-associated decisions, commands and lessons before falling back to text search.
- Prefer recent active decisions over old superseded notes.
- Do not load all memory without a specific reason.
- Use `.codex/context-api` through `open_context()` for persistent retrieval.
- Retrieve lessons by category or query when diagnosing repeated failures.
- Retrieve lessons by `task_id` when reviewing what was learned during a specific task.
- Record a new lesson only when it is reusable across future tasks; otherwise record a task log.
