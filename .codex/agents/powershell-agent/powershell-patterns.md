# PowerShell Patterns

- Directory creation: `New-Item -ItemType Directory -Force -Path "path"`.
- File search: `rg "pattern"`.
- Native recursive search fallback: `Get-ChildItem -Recurse | Select-String -Pattern "pattern"`.
- Virtual environment activation: `.\.venv\Scripts\Activate.ps1`.
- Store reusable command corrections through `open_context()` from `.codex/context-api`.
