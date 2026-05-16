---
name: powershell-recovery
description: Recover failed PowerShell commands using official context API command history and lessons
---

# Purpose

Make terminal work safe and self-correcting in PowerShell.

# Use this skill when

- A command fails.
- Bash syntax appears in PowerShell.
- Quoting, paths, encoding or destructive commands need review.

# Workflow

1. Retrieve relevant command history and lessons.
2. Validate command syntax for PowerShell.
3. Detect Bash incompatibilities.
4. Correct paths and quoting.
5. Block dangerous commands unless approved.
6. Record failed and corrected commands.
7. Save reusable lessons.

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

Ask before destructive commands, privileged commands, real `.env` edits or writes outside the workspace.

# Coordination

Support any agent that needs shell execution and route unexplained failures to debugging.

# Validation

Confirm corrected command is safe for Windows PowerShell before retrying.

# Error recovery

If retry fails, stop blind retries and diagnose root cause.

# Output format

Return failed command, error, corrected command, retry result and lesson.

# Avoid

- Bash syntax in PowerShell.
- Blind retries.
- Recording secrets in command logs.
