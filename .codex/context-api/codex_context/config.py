from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


class ConfigError(RuntimeError):
    """Raised when the local database configuration is incomplete."""


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str

    @property
    def safe_label(self) -> str:
        return f"{self.user}@{self.host}:{self.port}/{self.name}"

    @property
    def sqlalchemy_url(self) -> str:
        user = quote_plus(self.user)
        password = quote_plus(self.password)
        host = self.host
        database = quote_plus(self.name)
        return f"mysql+pymysql://{user}:{password}@{host}:{self.port}/{database}?charset=utf8mb4"


def load_config() -> DatabaseConfig:
    load_dotenv(ENV_PATH)

    missing = [
        key
        for key in (
            "CODEX_DB_HOST",
            "CODEX_DB_PORT",
            "CODEX_DB_NAME",
            "CODEX_DB_USER",
            "CODEX_DB_PASSWORD",
        )
        if not os.getenv(key)
    ]
    if missing:
        joined = ", ".join(missing)
        raise ConfigError(f"Missing required environment variable(s): {joined}")

    try:
        port = int(os.environ["CODEX_DB_PORT"])
    except ValueError as exc:
        raise ConfigError("CODEX_DB_PORT must be an integer.") from exc

    return DatabaseConfig(
        host=os.environ["CODEX_DB_HOST"],
        port=port,
        name=os.environ["CODEX_DB_NAME"],
        user=os.environ["CODEX_DB_USER"],
        password=os.environ["CODEX_DB_PASSWORD"],
    )
