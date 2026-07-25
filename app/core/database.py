from typing import Generator

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logger import get_logger
from app.models.base import Base

logger = get_logger(__name__)

# Engine with automatic connection pre-ping
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Session maker per request/task
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing transactional database sessions."""
    db = SessionLocal()
    try:
        yield db
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unhandled database session error")
        raise
    finally:
        db.close()


def get_database_status() -> tuple[bool, str]:
    """Validate DB connection and report database connectivity details."""
    try:
        expected_db = make_url(settings.DATABASE_URL).database
    except Exception:
        expected_db = None

    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT current_database() AS db_name,
                           current_user AS db_user,
                           inet_server_addr()::text AS db_host,
                           inet_server_port() AS db_port
                    """
                )
            ).mappings().one()

        connected_db = row["db_name"]
        if expected_db and connected_db != expected_db:
            msg = f"Connected to unexpected DB '{connected_db}' (expected '{expected_db}')"
            logger.error(msg)
            return False, msg

        msg = f"PostgreSQL connected successfully: db={connected_db}, user={row['db_user']}, host={row['db_host']}, port={row['db_port']}"
        logger.info(msg)
        return True, msg
    except Exception as exc:
        msg = f"Failed to connect to PostgreSQL: {exc}"
        logger.error(msg)
        return False, msg