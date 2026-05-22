# Orchestration Policy

## When to use subagents

Use subagents for:

- explicit user requests for orchestration or parallel agent work
- complex tasks
- cross-domain tasks
- implementation + validation + documentation
- tasks requiring different responsibilities

## Workflow

1. Identify work areas.
2. Select relevant agents.
3. Select relevant skills.
4. Let orchestrator assign best agent.
5. Keep implementation, validation and documentation separate.

## Rules

- Do not bypass orchestrator when the user explicitly asks for orchestration or when work is complex, cross-domain, multi-file or multi-agent.
- Simple scoped work may proceed without orchestrator, even when it has multiple small steps.
- Agent selection must be explicit.
