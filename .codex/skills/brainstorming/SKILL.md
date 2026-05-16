---
name: brainstorming
description: Explore intent, requirements and design before implementation with official context API memory
---

# Purpose

Prevent premature implementation by turning ideas into clear, approved designs.

# Use this skill when

- Creating features, components, workflows or behavior.
- Modifying agent or skill definitions.
- A request needs design choices, trade-offs or approval before edits.

# Workflow

1. Explore project context, including recent decisions from memory.
2. Ask clarifying questions one at a time when needed.
3. Propose 2-3 approaches with trade-offs.
4. Recommend one approach.
5. Present the design and request approval before implementation.
6. Save a spec when the design is substantial or the user asks for one.
7. Record accepted decisions and follow-up tasks.

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

Do not implement until the user approves the proposed design. For visual work, offer the visual companion in `visual-companion.md` before visual exploration.

# Coordination

Hand approved designs to orchestrator or implementation skill depending on complexity.

# Validation

Check the design for contradictions, missing constraints, unclear ownership and unapproved assumptions.

# Error recovery

If MariaDB is unavailable, keep using `open_context()` or `codex_memory.py`; the context API selects SQLite or file fallback internally.

# Output format

Return context found, options, recommendation, proposed design and approval request.

# Avoid

- Implementing before approval.
- Asking many questions at once.
- Designing beyond the requested scope.
- Storing secrets or full environment files.

# Existing assets

This skill keeps its companion files:

- `spec-document-reviewer-prompt.md`
- `visual-companion.md`
- `prompts/`
- `scripts/`
