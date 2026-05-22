---
name: context-recovery
description: Recover relevant project context from official context API memory before planning or implementation
---

# Purpose

Recover concise, relevant project context before work begins.

# Use this skill when

- Starting a task.
- Resuming after compaction.
- Investigating repeated errors.
- Preparing an agent or subagent.

# Workflow

1. Open memory through `.codex/context-api`.
2. Retrieve relevant pending tasks.
3. Retrieve recent decisions.
4. Retrieve relevant lessons.
5. Retrieve command history when terminal work is expected.
6. Detect contradictions or missing information.
7. Report backend status only when diagnostics are relevant.

# Memory Policy

Strictly follow memory and execution policies defined in .codex/API.md and .codex/AGENTS.md.

# Approval gates

Ask before reading sensitive files or expanding retrieval beyond relevant context.

# Coordination

Provide concise context packets to orchestrator and specialized agents.

# Validation

Confirm that retrieved context references `.codex/context-api` and uses `open_context()`.

# Error recovery

If MariaDB fails, keep using `open_context()` or `codex_memory.py`; the context API selects SQLite or file fallback internally.

# Output format

Return pending tasks, recent decisions, relevant lessons, command risks and contradictions.

# Avoid

- Full database dumps.
- Secret exposure.
- Treating Markdown mirrors as primary memory.
