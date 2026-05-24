from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import Config
from models import Base

engine = create_engine(Config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    return SessionLocal()
