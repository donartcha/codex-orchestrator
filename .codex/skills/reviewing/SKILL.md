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

# Memory Policy

Strictly follow memory and execution policies defined in .codex/API.md and .codex/AGENTS.md.

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
