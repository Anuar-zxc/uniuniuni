import logging
import time
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    kwargs: dict = {"pool_pre_ping": True}
    if get_settings().is_serverless and not url.startswith("sqlite"):
        # Function instances come and go; let the managed pooler (e.g. Neon's) own the connections.
        kwargs = {"poolclass": NullPool}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    eng = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(eng, "connect")
        def _fk_on(dbapi_conn, _):  # enforce ON DELETE CASCADE like Postgres
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return eng


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Idempotent schema creation. Several cold-starting instances may race on first deploy: retry once."""
    import app.models  # noqa: F401  (register models)

    for attempt in range(3):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception:  # pragma: no cover - only on concurrent first boot
            if attempt == 2:
                raise
            logging.getLogger(__name__).warning("create_all raced with another instance; retrying")
            time.sleep(1.5)
