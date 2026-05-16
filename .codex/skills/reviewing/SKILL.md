---
name: reviewing
description: Review changes for bugs, regressions and policy violations with official context API context
---

# Purpose

Detect correctness, safety, regression and maintainability risks.

# Use this skill when

- Reviewing code or docs.
- Checking a completed implementation.
- Assessing risk before finalizing.

# Workflow

1. Retrieve relevant decisions and constraints.
2. Inspect changed files.
3. Prioritize bugs and regressions.
4. Classify severity.
5. Record durable findings or follow-ups.

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

Ask before making fixes unless review scope includes remediation.

# Coordination

Send actionable findings to orchestrator or implementation-agent.

# Validation

Ground findings in file references, behavior or command output.

# Error recovery

If context conflicts with code, surface the contradiction and request resolution.

# Output format

Findings first, then questions, then brief summary and test gaps.

# Avoid

- Preference-only findings.
- Overengineering.
- Unverified speculation.
