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

# Memory Policy

Strictly follow memory and execution policies defined in .codex/API.md and .codex/AGENTS.md.

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
