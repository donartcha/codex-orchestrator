from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from .models import ArchitecturalDecision, CommandHistory, LessonLearned, Task, TaskLog
from .sanitizer import sanitize_memory


@dataclass(frozen=True)
class Contradiction:
    kind: str
    ids: tuple[int, ...]
    message: str


@dataclass(frozen=True)
class CompactionReport:
    duplicate_decision_keys: tuple[str, ...]
    inactive_decisions: int
    suggested_action: str


def build_memory_state(context, limit: int = 100) -> dict[str, Any]:
    state = {
        "tasks": [_model_payload(row) for row in context.tasks("pending", limit=limit)],
        "task_logs": [_model_payload(row) for row in context.task_logs(limit=limit)],
        "decisions": [_model_payload(row) for row in context.decisions(limit=limit)],
        "commands": [_model_payload(row) for row in context.commands(limit=limit)],
        "lessons": [_model_payload(row) for row in context.lessons(limit=limit)],
    }
    sanitized, _report = sanitize_memory(state)
    return sanitized


def serialize_memory_state(context, limit: int = 100) -> str:
    return json.dumps(build_memory_state(context, limit=limit), indent=2, default=str, ensure_ascii=False)


def detect_contradictions(decisions: list[ArchitecturalDecision]) -> list[Contradiction]:
    by_key: dict[str, list[ArchitecturalDecision]] = {}
    for decision in decisions:
        if decision.status != "active":
            continue
        by_key.setdefault(decision.decision_key, []).append(decision)
    contradictions: list[Contradiction] = []
    for key, rows in by_key.items():
        if len(rows) > 1:
            contradictions.append(
                Contradiction(
                    kind="duplicate_active_decision_key",
                    ids=tuple(int(row.id) for row in rows),
                    message=f"Multiple active decisions share key {key!r}.",
                )
            )
    return contradictions


def compact_memory(decisions: list[ArchitecturalDecision]) -> CompactionReport:
    duplicate_keys = tuple(item.message for item in detect_contradictions(decisions))
    inactive_count = sum(1 for decision in decisions if decision.status and decision.status != "active")
    return CompactionReport(
        duplicate_decision_keys=duplicate_keys,
        inactive_decisions=inactive_count,
        suggested_action="Review duplicate active decisions and supersede stale records; no destructive compaction was run.",
    )


def _model_payload(row: Task | TaskLog | ArchitecturalDecision | CommandHistory | LessonLearned) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in vars(row).items():
        if key.startswith("_"):
            continue
        payload[key] = value
    return payload


def report_to_dict(report: object) -> dict[str, Any]:
    return asdict(report)
