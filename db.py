from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import Config
from models import Base

engine = create_engine(Config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # Ignore DB initialization errors (e.g., on read-only filesystems like Vercel)
        print(f"⚠️ Warning: Could not initialize database: {e}")
        pass


def get_db() -> Session:
    try:
        return SessionLocal()
    except Exception:
        return None
