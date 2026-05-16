from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import DatabaseConfig, load_config


def create_db_engine(config: DatabaseConfig | None = None) -> Engine:
    db_config = config or load_config()
    return create_engine(
        db_config.sqlalchemy_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        future=True,
    )


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine or create_db_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        bound_engine = engine or session.get_bind()
        if bound_engine is not None:
            bound_engine.dispose()
