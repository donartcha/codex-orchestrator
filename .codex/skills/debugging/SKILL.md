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

# Memory Policy

Strictly follow memory and execution policies defined in .codex/API.md and .codex/AGENTS.md.

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
