import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import settings

logger = logging.getLogger(__name__)

# Engine configuration with pool_pre_ping to discard stale connections
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 3},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency that creates and provides a transactional database session,

    guaranteeing clean session closure upon completion or error.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health(timeout_seconds: float = 3.0) -> bool:
    """Executes a lightweight 'SELECT 1' connectivity probe against PostgreSQL.

    Catches all internal connection/driver errors without exposing credentials
    or internal tracebacks to callers.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            scalar = result.scalar()
            return scalar == 1
    except Exception as exc:
        # Structured log without credentials or raw traceback leakage to user
        logger.warning(
            "Database connectivity probe failed: %s",
            exc.__class__.__name__,
        )
        return False
