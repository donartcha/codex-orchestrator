---
name: context-recovery
description: Recover relevant project context from official context API memory before planning or implementation
---

# Purpose

Recover concise, relevant project context before work begins.

# Use this skill when

- Starting a task.
- Resuming after compaction.
- Investigating repeated errors.
- Preparing an agent or subagent.

# Workflow

1. Open memory through `.codex/context-api`.
2. Retrieve relevant pending tasks.
3. Retrieve recent decisions.
4. Retrieve relevant lessons.
5. Retrieve command history when terminal work is expected.
6. Detect contradictions or missing information.
7. Report backend status only when diagnostics are relevant.

# Memory usage

Use `.codex/context-api`:

```python
from codex_context.context import open_context
```

From terminal, use `python codex_memory.py ...` in `.codex/context-api`.

Backend fallback is transparent. Do not assume MariaDB or SQLite, do not open backend-specific connections, and use `backend-status` only for diagnostics.

Before:
- retrieve only relevant tasks, decisions, lessons and command history

During:
- persist important decisions, commands, errors and corrections

After:
- update task state
- save reusable lessons
- create follow-up tasks if needed

Do not:
- store secrets
- dump `.env`
- load irrelevant historical context
- duplicate records unnecessarily

# Approval gates

Ask before reading sensitive files or expanding retrieval beyond relevant context.

# Coordination

Provide concise context packets to orchestrator and specialized agents.

# Validation

Confirm that retrieved context references `.codex/context-api` and uses `open_context()`.

# Error recovery

If MariaDB fails, keep using `open_context()` or `codex_memory.py`; the context API selects SQLite or file fallback internally.

# Output format

Return pending tasks, recent decisions, relevant lessons, command risks and contradictions.

# Avoid

- Full database dumps.
- Secret exposure.
- Treating Markdown mirrors as primary memory.
