from typing import Generator
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker,Session
from app.core.config import settings

#Create the SQLAlchemy engine uisng the DATABASE_URL from settings

engine = create_engine(
    settings.DATABASE_URL,
    echo = True, #Set to false in production
    pool_pre_ping = True
)


#Create a configured session factory
SessionLocal = sessionmaker(
    autocommit = False,
    autoflush = False,
    bind =engine
)


def get_db() -> Generator[Session, None, None]:
    """
        FastAPI dependency that yields a databasesession per request
        and automatically closes it when the request is finished.

    """
    db = SessionLocal()
    try:
        yield db
    finally :
        db.close()

        
