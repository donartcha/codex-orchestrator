---
name: testing
description: Plan, run and record tests with official context API command history and lessons
---

# Purpose

Validate behavior with focused, meaningful tests.

# Use this skill when

- Adding or changing tests.
- Running validation.
- Investigating coverage gaps or flaky tests.

# Workflow

1. Retrieve testing lessons.
2. Detect framework and commands.
3. Run focused tests.
4. Fix test issues or report blockers.
5. Record command results and coverage follow-ups.

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

Ask before tests require external services, destructive fixtures or new dependencies.

# Coordination

Work with implementation-agent and debugging-agent on failures.

# Validation

Report command, result, failures and residual risk.

# Error recovery

Diagnose flaky behavior before weakening tests.

# Output format

Return commands run, pass/fail status, fixes, failures and follow-ups.

# Avoid

- Empty tests.
- Product changes only to satisfy weak tests.
- Hiding flaky failures.
