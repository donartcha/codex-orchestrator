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
    all_tasks = context.tasks(status="all", limit=None)
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
.\.venv\Scripts\python.exe codex_memory.py bootstrap --mode new-task --title "Add CI workflow"
.\.venv\Scripts\python.exe codex_memory.py backend-status
.\.venv\Scripts\python.exe codex_memory.py task list --status all
.\.venv\Scripts\python.exe codex_memory.py task summary
.\.venv\Scripts\python.exe codex_memory.py snapshot list
```

### Bootstrap modes

`bootstrap` is scoped by default. The default mode is `new-task`, not the old recent-memory dump.

```powershell
.\.venv\Scripts\python.exe codex_memory.py bootstrap --mode general --limit 5
.\.venv\Scripts\python.exe codex_memory.py bootstrap --mode new-task --title "Add CI workflow"
.\.venv\Scripts\python.exe codex_memory.py bootstrap --mode continue-task --task-id 6
.\.venv\Scripts\python.exe codex_memory.py bootstrap --mode debugging --query "PowerShell typer"
.\.venv\Scripts\python.exe codex_memory.py bootstrap --mode validation --category tests
```

Modes:

- `new-task`: default. Shows runtime warnings, backend status, pending tasks, active global or relevant decisions, and relevant lessons only when scoped by title/query/category/tags. Historical failed commands are skipped.
- `general`: manual full overview with recent tasks, decisions, lessons and historical diagnostics.
- `continue-task`: requires `--task-id`; shows task details, task logs, related decisions, validations, commands and lessons.
- `debugging`: requires `--query` or `--category`; shows matching failed commands, lessons and relevant decisions.
- `validation`: shows recent validation records, failed validations and commands related to tests, hooks and builds.

Useful bootstrap filters:

```text
--category
--tags
--task-id
--status
--agent
--query
--active-only
--unresolved-only
```

Failed commands are marked as `diagnostic=resolved` when a correction is recorded, otherwise `diagnostic=unresolved`.

### Task listing

`task list` defaults to `--status pending`. Output is explicit about the filter, for example `0 pending task(s).`, and also prints `Total task count: N task(s).` when total context is available.

If the selected status has no rows but other statuses exist, the CLI prints:

```text
Other task statuses exist.
```

Use `--status all` for all task rows:

```powershell
.\.venv\Scripts\python.exe codex_memory.py task list --status pending
.\.venv\Scripts\python.exe codex_memory.py task list --status all
```

Use `task summary` for grouped counts:

```powershell
.\.venv\Scripts\python.exe codex_memory.py task summary
```

Example:

```text
Pending: 0
Done: 12
Blocked: 1
Archived: 4
```
