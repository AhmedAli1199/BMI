from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from notetaker.config import settings


class Base(DeclarativeBase):
    pass


def _engine(url: str):
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
    return create_engine(url, **kw)


engine = _engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


# Columns added after the first release. create_all only makes missing tables, so existing installs get
# these added here - each is safe to run again.
UPGRADES = [
    ("clients", "notes_style", "VARCHAR(20) DEFAULT 'general'"),
    ("clients", "key_hint", "VARCHAR(20)"),
    ("clients", "is_active", "BOOLEAN DEFAULT TRUE"),
    ("clients", "last_used_at", "TIMESTAMP WITH TIME ZONE"),
    ("clients", "gemini_key_enc", "TEXT"),
    ("clients", "gemini_key_hint", "VARCHAR(12)"),
    ("clients", "max_concurrent", "INTEGER"),
    ("clients", "zoom_client_id", "VARCHAR(100)"),
    ("clients", "zoom_secret_enc", "TEXT"),
    ("clients", "zoom_secret_hint", "VARCHAR(12)"),
    ("clients", "zoom_status", "VARCHAR(20)"),
    ("clients", "zoom_error", "TEXT"),
    ("clients", "bot_project_id", "VARCHAR(64)"),
    ("clients", "bot_key_enc", "TEXT"),
    ("clients", "bot_webhook_secret_enc", "TEXT"),
    ("meetings", "ends_at", "TIMESTAMP WITH TIME ZONE"),
    ("meetings", "ai_input_tokens", "INTEGER DEFAULT 0"),
    ("meetings", "ai_output_tokens", "INTEGER DEFAULT 0"),
]


def init_db(bind=None) -> None:
    from sqlalchemy import inspect, text
    from notetaker import models  # noqa: F401 - registers the tables
    bind = bind or engine
    Base.metadata.create_all(bind)
    have = {t: {c["name"] for c in inspect(bind).get_columns(t)} for t in {u[0] for u in UPGRADES}}
    with bind.begin() as conn:
        for table, col, ddl in UPGRADES:
            if col not in have.get(table, set()):
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
