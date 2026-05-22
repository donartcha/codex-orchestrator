# Fallback Policy

## Fallback vs Recovery

- fallback = alternate safe path
- recovery = fixing the failing path

## Examples

- global Python fails -> workspace `.venv`
- bash syntax fails -> convert to PowerShell
- MariaDB unavailable -> Context API selects SQLite or file fallback

## Rules

- Agents must not choose MariaDB, SQLite or file backend manually.
- Use the official Context API to handle backend selection.
- Record fallback when relevant.
- Fallback is not automatically a permanent solution.
