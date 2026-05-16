---
name: implementation
description: Implement small, safe changes while recording relevant context through the official context API
---

# Purpose

Apply scoped changes that satisfy an approved task.

# Use this skill when

- The design is approved.
- A small or medium code/docs change is ready.
- The task has clear files or behavior to modify.

# Workflow

1. Read relevant constraints and decisions.
2. Inspect existing patterns.
3. Apply the smallest useful change.
4. Validate incrementally.
5. Record commands and technical decisions.
6. Update task status or follow-ups.

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

Ask before new dependencies, broad refactors, destructive commands or `.env` edits.

# Coordination

Receive scope from orchestrator for complex work and return changed files and validation results.

# Validation

Run focused checks and record command outcomes.

# Error recovery

Use debugging or powershell-recovery when failures repeat.

# Output format

Return summary, changed files, validation, decisions and follow-ups.

# Avoid

- Unrelated edits.
- Massive refactors.
- Silent validation failures.
