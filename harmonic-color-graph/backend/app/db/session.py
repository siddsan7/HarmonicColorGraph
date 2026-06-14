from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def get_database_url() -> str:
    return get_settings().database_url


def create_database_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or get_database_url())


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    engine = create_database_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


SessionLocal = create_session_factory()


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
