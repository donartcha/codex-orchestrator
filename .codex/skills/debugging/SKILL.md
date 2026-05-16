---
name: debugging
description: Diagnose root causes using logs, command history and official context API lessons
---

# Purpose

Find and fix real root causes without repeating failed attempts.

# Use this skill when

- A command, test or workflow fails.
- The same error appears repeatedly.
- The cause is uncertain.

# Workflow

1. Retrieve similar command history and lessons.
2. Capture exact error text.
3. Form hypotheses.
4. Validate hypotheses one at a time.
5. Apply the smallest fix.
6. Record root cause and lesson.

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

Ask before risky fixes, destructive diagnostics or credential changes.

# Coordination

Coordinate with testing for reproducible failures and powershell-recovery for shell issues.

# Validation

A fix is valid when the observed failure is explained and revalidation passes.

# Error recovery

If a hypothesis fails, record it briefly and move to the next likely cause.

# Output format

Return symptom, root cause, evidence, fix, validation and lesson.

# Avoid

- Random changes.
- Blind retries.
- Ignoring persisted command history.
