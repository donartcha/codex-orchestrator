from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SECRET_PATTERNS = (
    ("password", re.compile(r"(?i)(password\s*[=:]\s*)([^\s;&|]+)")),
    ("api_key", re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)([^\s;&|]+)")),
    ("token", re.compile(r"(?i)(token\s*[=:]\s*)([^\s;&|]+)")),
    ("mysql_password_flag", re.compile(r"(?i)(?<!\w)(-p)([^\s;&|]+)")),
)
ENV_FILE_PATTERN = re.compile(r"(?i)(^|[\\/])\.env(?:\.[A-Za-z0-9_-]+)?$")
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)\b[A-Z]:\\[^\s\"']+")
UNIX_HOME_PATH = re.compile(r"(?<!\w)/(?:home|root)/[^\s\"']+")


@dataclass(frozen=True)
class SanitizationEvent:
    field_path: str
    kind: str


@dataclass(frozen=True)
class SanitizationReport:
    events: tuple[SanitizationEvent, ...]

    @property
    def changed(self) -> bool:
        return bool(self.events)


def sanitize_memory(data: dict[str, Any], repo_root: str | Path | None = None) -> tuple[dict[str, Any], SanitizationReport]:
    events: list[SanitizationEvent] = []
    sanitized = _sanitize_value(data, "$", Path(repo_root).resolve() if repo_root else None, events)
    if not isinstance(sanitized, dict):
        sanitized = {}
    return sanitized, SanitizationReport(tuple(events))


def detect_secrets(data: dict[str, Any]) -> list[SanitizationEvent]:
    _sanitized, report = sanitize_memory(data)
    return [event for event in report.events if event.kind in {"password", "api_key", "token", "mysql_password_flag", "env_file"}]


def normalize_paths(data: dict[str, Any], repo_root: str | Path) -> dict[str, Any]:
    sanitized, _report = sanitize_memory(data, repo_root=repo_root)
    return sanitized


def _sanitize_value(value: Any, field_path: str, repo_root: Path | None, events: list[SanitizationEvent]) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_value(item, f"{field_path}.{key}", repo_root, events)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _sanitize_value(item, f"{field_path}[{index}]", repo_root, events)
            for index, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return tuple(
            _sanitize_value(item, f"{field_path}[{index}]", repo_root, events)
            for index, item in enumerate(value)
        )
    if isinstance(value, str):
        return _sanitize_text(value, field_path, repo_root, events)
    return value


def _sanitize_text(text: str, field_path: str, repo_root: Path | None, events: list[SanitizationEvent]) -> str:
    sanitized = text
    for kind, pattern in SECRET_PATTERNS:
        sanitized, count = pattern.subn(lambda match: f"{match.group(1)}[REDACTED]", sanitized)
        if count:
            events.append(SanitizationEvent(field_path, kind))
    if ENV_FILE_PATTERN.search(sanitized):
        sanitized = ENV_FILE_PATTERN.sub(r"\1[REDACTED_ENV]", sanitized)
        events.append(SanitizationEvent(field_path, "env_file"))
    sanitized = _normalize_path_text(sanitized, field_path, repo_root, events)
    return sanitized


def _normalize_path_text(text: str, field_path: str, repo_root: Path | None, events: list[SanitizationEvent]) -> str:
    sanitized = text
    if repo_root is not None:
        root_text = str(repo_root)
        if root_text in sanitized:
            sanitized = sanitized.replace(root_text, "${REPO_ROOT}")
            events.append(SanitizationEvent(field_path, "repo_path"))
    sanitized, windows_count = WINDOWS_ABSOLUTE_PATH.subn("[REDACTED_PATH]", sanitized)
    if windows_count:
        events.append(SanitizationEvent(field_path, "local_path"))
    sanitized, unix_count = UNIX_HOME_PATH.subn("[REDACTED_PATH]", sanitized)
    if unix_count:
        events.append(SanitizationEvent(field_path, "local_path"))
    return sanitized
