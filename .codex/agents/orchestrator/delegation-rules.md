# Delegation Rules

- Use specialized agents when a task has distinct implementation, review, testing, debugging, documentation or shell execution work.
- Keep write scopes disjoint when agents run in parallel.
- Require every subagent to return summary, risks, affected files and validations.
- Consolidate all results before final response and update memory through `open_context()`.
