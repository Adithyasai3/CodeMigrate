"""Database engine/session (SQLite by default; Postgres via DATABASE_URL)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from codemigrate.config import get_settings

_engine = None


def get_engine(url: str | None = None):
    global _engine
    if _engine is None or url:
        url = url or get_settings().database_url
        args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=args, pool_pre_ping=True)
    return _engine


def init_db(url: str | None = None) -> None:
    from codemigrate.api import models  # noqa: F401 - registers tables

    SQLModel.metadata.create_all(get_engine(url))


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
