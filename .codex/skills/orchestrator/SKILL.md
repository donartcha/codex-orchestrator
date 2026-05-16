---
name: orchestrator
description: Plan, decompose, delegate and consolidate complex Codex tasks with official context API memory
---

# Purpose

Coordinate complex work through memory bootstrap, decomposition, agent assignment, validation, review and final memory update.

# Use this skill when

- A task spans multiple files, phases or specialties.
- The user asks for subagents or delegation.
- Implementation, testing, review and documentation need coordination.

# Workflow

1. Bootstrap memory from `.codex/context-api`.
2. Summarize relevant tasks, decisions, lessons and command history.
3. Decompose the task and identify dependencies.
4. Assign specialized agents.
5. Consolidate results.
6. Run or request validation and review.
7. Update memory and report outcome.

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

Ask before destructive commands, broad scope changes, new dependencies or real `.env` edits.

# Coordination

Use agent definitions in `.codex/agents/` and keep write scopes disjoint.

# Validation

Require each assigned agent to report validations, files affected, risks and blockers.

# Error recovery

Route shell failures to powershell-agent and behavioral failures to debugging-agent or testing-agent.

# Output format

Return plan, assignments, results, validations, risks and memory updates.

# Avoid

- Duplicate tasks.
- Parallel agents editing the same files.
- Skipping review on risky changes.
