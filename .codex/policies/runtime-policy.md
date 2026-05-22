# Runtime Policy

## Python runtime resolution

Resolve Python before substantial work.

Preferred interpreter order:

- `.codex/context-api/.venv/Scripts/python.exe`
- workspace-managed environments
- system Python only as a last resort

## Runtime commands

```powershell
.\.venv\Scripts\python.exe codex_memory.py resolve-python
.\.venv\Scripts\python.exe codex_memory.py runtime-check
```

## Execution context

Treat the active interpreter, shell and backend as the execution context.

Do not continue substantial Python work if runtime validation fails unless a safe recovery path is applied.

Runtime status handling:

- `OK`: continue.
- `WARNING`: continue when the warning does not affect the task; record relevant warnings in memory during finish or command history.
- `FALLBACK_USED`: continue only if the fallback is safe for the task, and record the fallback when relevant.
- `ERROR`: stop unless a safe recovery or fallback path is applied.

Ask the user what to do before continuing only when a `WARNING` or fallback can affect behavior, data safety, validation trust or expected outputs.

## File encoding

- Preserve existing file encoding when reading files.
- New and modified text files should be UTF-8 without BOM unless a file already uses another encoding for a documented reason.
- Do not introduce BOM markers.
- For PowerShell writes, prefer APIs or commands that explicitly write UTF-8 without BOM.
- If encoding is uncertain for a critical file, inspect it before editing.

## PowerShell UTF-8 session policy

When using PowerShell for agent work, initialize UTF-8 at session start before substantial commands.

Use:

```powershell
[Console]::InputEncoding  = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding           = [System.Text.UTF8Encoding]::new($false)
chcp 65001 > $null
```

Validation rule:

- If `runtime-check` reports `WARNING: stdout encoding is cp1252`, apply the UTF-8 initialization once and retry `runtime-check`.
- If UTF-8 round-trip remains valid after retry, work may continue with warning recorded.
- If UTF-8 round-trip fails, treat as runtime risk and recover before editing critical files.
