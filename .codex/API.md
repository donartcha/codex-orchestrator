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
    context.remember_lesson("testing", "Task problem", "Task solution", "Prevention", task_id=1)
    task_lessons = context.lessons(category="testing", task_id=1, limit=10)
    children = context.task_children(parent_task_id=1)
    tree = context.task_tree(root_task_id=1)
    context.update_task(task_id=2, title="Updated step", sort_order=2)
    context.reorder_task(task_id=2, sort_order=3)
```

Decisions, commands, lessons and snapshots accept nullable `task_id` values. Omit `task_id` for global memory; pass it when the record belongs to one task execution and should be retrievable with `--task-id`.

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
.\.venv\Scripts\python.exe codex_memory.py lesson add --category "powershell" --problem "What failed" --solution "What fixed it" --prevention "How to avoid it"
.\.venv\Scripts\python.exe codex_memory.py lesson list --limit 10
.\.venv\Scripts\python.exe codex_memory.py lesson list --task-id 1 --limit 10
.\.venv\Scripts\python.exe codex_memory.py snapshot list
```

`finish` records a task log and optional task status. It does not record reusable lessons. Use `lesson add` when a pattern should be available to future agents.

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
- Task-scoped decisions, commands and lessons are matched by their stored `task_id`; global records remain available through normal list/query modes.
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

### Lessons

Lessons are reusable root causes, corrections and prevention strategies. They are not task summaries.

```powershell
.\.venv\Scripts\python.exe codex_memory.py lesson add --category "ci" --problem "Tests depended on generated files in a warm workspace" --solution "Build required artifacts before tests" --prevention "Validate scripts from a clean checkout"
.\.venv\Scripts\python.exe codex_memory.py lesson add --task-id 1 --category "ci" --problem "Task-specific CI failure" --solution "Fix for this task" --prevention "Check before similar task work"
.\.venv\Scripts\python.exe codex_memory.py lesson list --category "ci" --limit 10
```

Record a lesson when the learning is likely to prevent a future failure. Record a `task log` when the note only explains what happened in the current task.
