# Validation Policy

- Validate the smallest meaningful behavior first.
- Prefer existing project commands.
- Record validation commands and failures with `remember_command()`.
- Revalidate after fixes.
- Access command memory through `open_context()` from `.codex/context-api`.
