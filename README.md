# Codex Orchestrator

This repository contains Codex orchestration configuration, local context tooling and durable project guidance. It is intentionally portable: committed files should work from any clone without depending on one developer's workstation layout.

## Pre-Commit Validation

Install the hook runner once per Python environment:

```powershell
pip install pre-commit
pre-commit install
```

Run the full validation suite before larger changes:

```powershell
pre-commit run --all-files
```

The repository-level hooks check for:

- trailing whitespace and missing final newlines
- private keys and likely secrets
- newly added large files
- local absolute paths from workstation-specific roots
- SQLite database artifacts
- committed `.env` files
- committed `.venv` or `venv` directories
- accidental Bash-only commands in portable docs and scripts

## Validation Philosophy

Prefer repository-relative paths such as `.codex/...` and document commands in PowerShell form unless a file is intentionally a shell script. Local runtime state belongs outside version control; use examples, templates and setup instructions instead of committing generated databases, virtual environments or real environment files.

These checks are meant to catch portability mistakes early without blocking normal repository-relative paths or intentional script files.
