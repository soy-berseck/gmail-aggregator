from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config import Config
from models import Base


def _build_engine():
    """Build a SQLAlchemy engine.

    For in-memory SQLite (used on Vercel because the filesystem is read-only)
    we MUST use StaticPool so every session shares the same underlying
    connection — otherwise each session sees an empty database.
    """
    url = Config.DATABASE_URL
    if url.startswith("sqlite") and ":memory:" in url:
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url, connect_args={"check_same_thread": False})


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine)

# Track whether schema has been initialized in this process. On Vercel each
# cold start re-runs init_db() against a fresh in-memory DB, which is what we
# want (tokens live only for the lifetime of the warm Lambda).
_initialized = False


def init_db():
    global _initialized
    try:
        Base.metadata.create_all(bind=engine)
        _initialized = True
    except Exception as e:
        print(f"WARNING: Could not initialize database: {e}")


def get_db() -> Session:
    """Return a session, ensuring the schema exists.

    On serverless platforms a warm container may serve a request before
    init_db() has been re-run, so we lazily create the schema if needed.
    """
    global _initialized
    try:
        if not _initialized:
            try:
                Base.metadata.create_all(bind=engine)
                _initialized = True
            except Exception as e:
                print(f"WARNING: lazy create_all failed: {e}")
        return SessionLocal()
    except Exception as e:
        print(f"WARNING: get_db failed: {e}")
        return None
