# Codex Context API Reference

The official persistence interface is:

```python
from codex_context.context import open_context
```

Use facade methods on `CodexContext` for tasks, task logs, orchestration records, decisions, commands, lessons, snapshots, contradictions and compaction reports.

## Facade

```python
with open_context() as context:
    context.remember_task("Title", "Description", assigned_agent="codex")
    pending = context.tasks(status="pending", limit=5)
    context.remember_task_log(task_id=1, content="Validated", log_type="validation")
    context.remember_orchestration_execution("exec-0001", "Title", "Description", "orchestrator", "root-exec-0001")
    context.remember_orchestration_task("root-exec-0001", "exec-0001")
    context.remember_orchestration_validation("root-exec-0001", "pytest", True, "ok")
    context.remember_decision("key", "Title", "Rationale", "Consequences")
    context.remember_command("codex", "powershell", "pytest tests -v", True)
    context.remember_lesson("testing", "Problem", "Solution", "Prevention")
```

## Lifecycle

```python
with open_context() as context:
    snapshot = context.remember_snapshot(title="pre-change", limit=100)
    snapshots = context.snapshots(limit=10)
    context.supersede_decision(old_id=1, new_id=2)
    contradictions = context.contradictions()
    compaction = context.compact_memory()
```

`snapshot restore` is not enabled yet.

## Backend Contract

Backends implement the callable surface defined in:

```python
from codex_context.backends import validate_backend_contract
```

SQLite and file parity is covered by `tests/test_backend_parity.py`.

Orchestration persistence follows the same backend chain as all other memory: MariaDB primary, SQLite fallback, then the file emergency fallback. `.codex/context-api/orchestration` and `.codex/context/orchestration` are legacy runtime JSON locations and are ignored by Git.

## Sanitization

Facade writes are sanitized before persistence. Secret values and local absolute paths are redacted irreversibly. Sanitization reports include only field path and pattern kind metadata.

## CLI

Use:

```powershell
cd .codex/context-api
.\.venv\Scripts\python.exe codex_memory.py bootstrap --limit 5
.\.venv\Scripts\python.exe codex_memory.py backend-status
.\.venv\Scripts\python.exe codex_memory.py snapshot list
```
