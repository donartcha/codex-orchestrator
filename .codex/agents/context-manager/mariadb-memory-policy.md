# Context API Memory Policy

Persistent memory is accessed only through `.codex/context-api/codex_context/context.py`:

```python
from codex_context.context import open_context
```

Backend selection is transparent inside `.codex/context-api`: MariaDB primary, SQLite fallback, JSON/Markdown emergency fallback. Agents do not choose backends and should use `backend-status` only for diagnostics.

If the facade lacks a needed method, document the gap and propose a clean extension.
