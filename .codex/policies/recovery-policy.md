# Recovery Policy

## Safe recovery workflow

1. Capture exact command.
2. Capture exact error text.
3. Search relevant lessons and command history.
4. Decide recovery or fallback.
5. Retry only when safe.
6. Record reusable lessons through official Context API.
7. Never store secrets, tokens, passwords or credentials.

## Additional rules

- Do not retry blindly.
- Do not hide failed commands.
- Prefer minimal safe retries.
- Convert shell syntax only when the target shell is confirmed.

## Filesystem permission recovery for runtime-check

When `codex_memory.py runtime-check` reports a filesystem permissions error while creating a `codex-runtime-*` temporary file under `.codex/context-api`, first determine whether this is a real NTFS permission issue or a sandbox restriction.

Known sandbox symptom:

```text
ERROR: filesystem permissions: PermissionError: [Errno 13] Permission denied:
 .codex/context-api/codex-runtime-...
```

If PowerShell can create and remove a file in `.codex/context-api`, but the workspace Python interpreter cannot, treat the failure as a sandbox write restriction for Python under `.codex`.

Safe recovery path:

```powershell
cd .codex/context-api
.\.venv\Scripts\python.exe codex_memory.py runtime-check
```

Run the command with approved execution outside the sandbox. If the retry reports `OK: filesystem permissions`, continue and record that the original error was sandbox-related. A remaining `WARNING` for `stdout encoding is cp1252` does not block work when UTF-8 data round-trips.

Do not edit project permissions, ACLs, or runtime code for this case unless the same filesystem error also occurs outside the sandbox.
