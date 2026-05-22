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

# Memory Policy

Strictly follow memory and execution policies defined in .codex/API.md and .codex/AGENTS.md.

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
