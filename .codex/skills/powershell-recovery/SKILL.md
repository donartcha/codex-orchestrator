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

# Memory Policy

Strictly follow memory and execution policies defined in .codex/API.md and .codex/AGENTS.md.

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
