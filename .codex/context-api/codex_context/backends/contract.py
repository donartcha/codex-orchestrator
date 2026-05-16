from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .base import ContextBackend


BACKEND_CONTRACT_METHODS = (
    "close",
    "session",
    "remember_task",
    "tasks",
    "set_task_status",
    "remember_snapshot",
    "snapshots",
    "remember_task_log",
    "task_logs",
    "remember_decision",
    "decisions",
    "supersede_decision",
    "remember_command",
    "commands",
    "remember_lesson",
    "lessons",
)


@runtime_checkable
class BackendContract(ContextBackend, Protocol):
    """Normalized persistence contract all context backends must expose."""


@dataclass(frozen=True)
class BackendContractReport:
    backend_name: str
    missing_methods: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing_methods


def validate_backend_contract(backend: object, required_methods: Iterable[str] = BACKEND_CONTRACT_METHODS) -> BackendContractReport:
    missing = tuple(name for name in required_methods if not callable(getattr(backend, name, None)))
    backend_status = getattr(backend, "status", None)
    backend_name = getattr(backend_status, "name", None) or getattr(backend, "name", type(backend).__name__)
    return BackendContractReport(str(backend_name), missing)
