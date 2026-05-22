# Validation Policy

## Validation requirements

Validate after substantial work.

Minimum runtime validation:

```powershell
.\.venv\Scripts\python.exe codex_memory.py runtime-check
```

If this fails with `PermissionError` while creating a `.codex/context-api/codex-runtime-*` temporary file, follow the filesystem permission recovery path in `recovery-policy.md` before treating validation as blocked.

Project-specific validation should come from relevant agent or skill docs.

## Recording validation

- Record validation results during finish.
- If validation cannot be run, record why.
- Do not claim validation passed unless it was executed successfully.
- Use `finish` or task logs for validation results that belong only to the current task.
- Use `lesson add` only for reusable causes, fixes or prevention patterns.
- Record relevant runtime `WARNING` or `FALLBACK_USED` states when they affect validation trust or future troubleshooting.

Example:

```powershell
.\.venv\Scripts\python.exe codex_memory.py finish --task-id 1 --summary "Validated focused docs update" --status done
.\.venv\Scripts\python.exe codex_memory.py lesson add --category "validation" --problem "What failed" --solution "What fixed it" --prevention "How to avoid it"
```

## Scope safety

- Do not modify unrelated files.
- Do not use validation as a reason to reformat or rewrite files outside the task scope.
- Report unrelated failures separately instead of hiding them in task changes.
