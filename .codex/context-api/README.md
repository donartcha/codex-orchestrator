# Codex Context API

Capa local para guardar memoria persistente de Codex mediante una fachada unica con fallback transparente.

## Proposito

Esta carpeta mantiene contexto durable para que Codex pueda recuperar tareas, decisiones, logs de tarea, comandos y aprendizajes sin depender solo del historial de conversacion.

La fuente oficial para agents, skills y CLIs es `open_context()` o `codex_memory.py`. MariaDB es el backend primario; SQLite y JSON/Markdown son fallbacks internos de emergencia.

## Arquitectura

- `codex_context/models.py`: modelos SQLAlchemy y tablas.
- `codex_context/repositories.py`: operaciones internas de persistencia.
- `codex_context/context.py`: fachada oficial para agents, skills y CLIs.
- `codex_context/fallback.py`: seleccion interna de backend.
- `codex_context/backends/`: backends MariaDB, SQLite y archivo.
- `codex_memory.py`: CLI oficial unificado.
- `scripts/*.py`: scripts legacy compatibles.

El codigo de agents, skills y CLIs debe usar:

```python
from codex_context.context import open_context
```

No abras sesiones SQLAlchemy ni conexiones MariaDB/SQLite directamente fuera de la capa interna. Agents y skills no eligen backend.

## MariaDB y `.env`

MariaDB se intenta primero. Si no esta disponible, `open_context()` usa SQLite. Si SQLite tampoco esta disponible, usa fallback JSON/Markdown. El fallback muestra un warning, pero el codigo de agents y skills no captura ni implementa esa decision.

Activa el entorno virtual desde PowerShell:

```powershell
cd .codex/context-api
.\.venv\Scripts\Activate.ps1
```

Instala dependencias si hace falta:

```powershell
pip install -r requirements.txt
```

Configura `.env` desde el ejemplo:

```powershell
copy .env.example .env
```

No imprimas ni guardes passwords reales en docs, logs, memoria o respuestas.

Inicializa tablas solo cuando sea necesario:

```powershell
python scripts/init_db.py
```

`init_db.py` crea tablas si no existen. No ejecuta migraciones destructivas.

## CLI oficial

Usa `codex_memory.py` como punto unico de entrada:

```powershell
python codex_memory.py check
python codex_memory.py resolve-python
python codex_memory.py runtime-check
python codex_memory.py env-status
python codex_memory.py backend-status
python codex_memory.py bootstrap --limit 5
python codex_memory.py finish --task-id 1 --summary "Resumen de lo hecho" --status done
python codex_memory.py status
```

## Resolucion de entorno Python

El CLI puede resolver el interprete correcto antes de ejecutar herramientas de contexto.

Prioridad:

```text
.venv/Scripts/python.exe
->
Poetry environment
->
uv-managed Python
->
pyenv
->
system Python
```

Comando:

```powershell
python codex_memory.py resolve-python
```

El resolvedor detecta virtualenv activo, valida imports minimos (`typer`, `sqlalchemy`, `pymysql`), reporta imports rotos y muestra warnings. No instala dependencias, no modifica `PATH` global y no toca `.env`.

Si Python global no tiene dependencias, usa el interprete local:

```powershell
.\.venv\Scripts\python.exe codex_memory.py bootstrap --limit 5
```

## Runtime validation

Validacion completa:

```powershell
python codex_memory.py runtime-check
python codex_memory.py env-status
```

Valida:

- Python interpreter
- virtualenv
- PowerShell
- active memory backend
- required imports
- `codex_memory.py` availability
- filesystem permissions
- UTF-8 compatibility
- shell compatibility

Estados posibles:

- `OK`
- `WARNING`
- `ERROR`
- `FALLBACK_USED`

## Recovery vs fallback

Recovery corrige el problema y reintenta la ruta original.

```text
bash command invalid in PowerShell
->
convert command
->
retry safely
```

Fallback usa una ruta alternativa.

```text
global python fails
->
use local .venv python
```

Recovery y fallback son complementarios.

## Backend fallback transparente

MariaDB es el backend primario. Si MariaDB falla, el contexto selecciona SQLite. Si SQLite falla, selecciona JSON/Markdown file fallback. Esto ocurre dentro de `.codex/context-api`.

```text
MariaDB unavailable
->
SQLite fallback
-> if SQLite unavailable
JSON/Markdown file fallback
->
show warning
```

Agents y skills deben seguir usando exactamente la misma interfaz:

```python
from codex_context.context import open_context
```

Tambien pueden inspeccionar estado sin controlar backend:

```powershell
python codex_memory.py backend-status
```

Uso correcto:

- Use `open_context()`.
- Use `python codex_memory.py ...`.
- Report backend status if relevant.

Uso incorrecto:

- Connect directly to MariaDB.
- Connect directly to SQLite.
- Implement fallback logic inside prompts, `AGENT.md` or `SKILL.md`.
- Duplicate persistence logic.

### Tasks

Tasks representan trabajo pendiente, en curso o finalizado.

```powershell
python codex_memory.py task add --title "Revisar API" --description "Validar CLI de memoria" --agent codex --priority high
python codex_memory.py task list --status pending --limit 20
python codex_memory.py task status --task-id 1 --status done
```

### Task logs

Task logs registran que ocurrio en una tarea concreta. No son lessons.

```powershell
python codex_memory.py task log --task-id 1 --content "Validacion completada" --agent codex --type validation
python codex_memory.py task logs --task-id 1 --limit 10
```

### Decisions

Decisions guardan decisiones tecnicas o arquitectonicas.

```powershell
python codex_memory.py decision add --key "memory-cli" --title "CLI unico" --rationale "Centraliza entradas y salidas de contexto"
python codex_memory.py decision list --limit 10
```

### Lessons

Lessons guardan aprendizajes reutilizables para el futuro.

```powershell
python codex_memory.py lesson add --category "powershell" --problem "Comando Bash usado en PowerShell" --solution "Usar cmdlets nativos" --prevention "Revisar shell antes de ejecutar"
python codex_memory.py lesson list --limit 10
```

### Commands

Commands guardan historial de ejecucion, errores y correcciones.

```powershell
python codex_memory.py command add --agent powershell-agent --shell powershell --command "python codex_memory.py check" --success true
python codex_memory.py command list --failed-only --limit 10
```

## Diferencias conceptuales

- `tasks`: trabajo que debe hacerse o ya se hizo.
- `task_logs`: que ocurrio en una tarea concreta.
- `decisions`: decisiones tecnicas o arquitectonicas.
- `lessons`: aprendizajes reutilizables para evitar errores futuros.
- `commands`: historial de ejecucion de terminal, incluyendo errores y correcciones.

## Flujo recomendado antes de trabajar

```powershell
cd .codex/context-api
.\.venv\Scripts\Activate.ps1
python codex_memory.py bootstrap --limit 5
```

## Flujo recomendado despues de trabajar

```powershell
python codex_memory.py finish --task-id 1 --summary "Resumen de lo hecho" --status done
```

Ver estado general:

```powershell
python codex_memory.py status
```

## Uso desde Python

```python
from codex_context.context import open_context

with open_context() as context:
    task = context.remember_task(
        title="Revisar memoria local",
        description="Guardar una tarea desde la API unificada.",
        assigned_agent="codex",
        priority="normal",
    )
    context.remember_task_log(
        task_id=task.id,
        content="Resumen de lo ocurrido en la tarea.",
        agent_name="codex",
        log_type="summary",
    )
    context.remember_command(
        agent_name="codex",
        shell_type="powershell",
        command_text="python codex_memory.py check",
        success_flag=True,
    )
    pending = context.tasks(status="pending", limit=5)
```

Helpers adicionales para recovery/fallback:

```python
from codex_context.context import open_context

with open_context() as context:
    context.remember_recovery_lesson(
        category="python-environment",
        problem_description="Global Python could not import typer.",
        solution_description="Fallback to workspace .venv Python.",
        prevention_strategy="Run resolve-python before Codex context tooling.",
    )
    context.remember_fallback_event(
        agent_name="codex_memory",
        shell_type="powershell",
        command_text="python codex_memory.py bootstrap --limit 5",
        fallback_from="C:\\Python313\\python.exe",
        fallback_to=".\\.venv\\Scripts\\python.exe",
        reason="missing typer",
    )
```

## Politica de seguridad

- No guardar secretos.
- No imprimir passwords.
- No volcar `.env`.
- No registrar tokens en `commands`, `task_logs`, `lessons` o `decisions`.
- Recuperar solo contexto reciente y relevante.
- Usar `open_context()` para la memoria persistente.

## Scripts legacy

Estos scripts se mantienen por compatibilidad, pero no son la primera opcion:

- `scripts/check_connection.py`
- `scripts/context_bootstrap.py`
- `scripts/context_finish.py`
- `scripts/add_task.py`
- `scripts/list_tasks.py`
- `scripts/update_task_status.py`
- `scripts/add_decision.py`
- `scripts/list_decisions.py`
- `scripts/add_lesson.py`
- `scripts/list_lessons.py`
- `scripts/add_command_log.py`
- `scripts/list_command_history.py`

Usa `python codex_memory.py ...` como CLI oficial.

## Tablas

`init_db.py` crea estas tablas si no existen:

- `context_snapshots`
- `architectural_decisions`
- `tasks`
- `task_logs`
- `command_history`
- `lessons_learned`
- `project_constraints`
- `context_embeddings`
- `agent_memory`
- `file_index`
