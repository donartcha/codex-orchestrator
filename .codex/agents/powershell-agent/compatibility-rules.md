# Compatibility Rules

- Replace Bash directory creation flags with `New-Item -ItemType Directory -Force`.
- Replace POSIX virtualenv activation with `.\.venv\Scripts\Activate.ps1`.
- Prefer `Get-ChildItem`, `Select-String`, `Remove-Item`, `Move-Item` and `Copy-Item`.
- Validate Windows paths and quoting.
- Check prior command lessons through `open_context()` before complex conversions.
