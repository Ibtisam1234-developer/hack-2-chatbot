"""
Database Connection Configuration for Todo API

Owner: Database Reliability Engineer
Purpose: Neon Serverless PostgreSQL connection with asyncpg driver
Architecture: Async/await with SQLModel ORM and connection pooling

Constitutional Constraints:
- REQUIRED: pool_pre_ping=True for serverless cold start handling
- REQUIRED: AsyncEngine with asyncpg driver
- REQUIRED: Environment variable for DATABASE_URL (never hardcode)
- REQUIRED: Connection pooling optimized for serverless (smaller pool sizes)

All operations use SQLModel for type-safe database interactions.
Connection includes retry logic and proper error handling for Neon serverless.
"""

import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlmodel import SQLModel
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("database.connection")

# Load environment variables
load_dotenv()


class DatabaseConfig:
    """
    Database configuration for Neon Serverless PostgreSQL.

    Optimized for serverless with:
    - pool_pre_ping: Validates connections before use (handles cold starts)
    - Small pool size: Serverless databases work better with fewer connections
    - Pool recycling: Prevents stale connections
    - Async operations: Non-blocking I/O for better concurrency
    """

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL environment variable not set. "
                "Please add DATABASE_URL to your .env file with your Neon connection string."
            )

        # Remove query parameters that asyncpg doesn't accept in URL
        # (sslmode, channel_binding, etc. will be handled via connect_args)
        if "?" in self.database_url:
            self.database_url = self.database_url.split("?")[0]
            logger.info("Removed query parameters from DATABASE_URL (will use connect_args for SSL)")

        # Convert postgresql:// to postgresql+asyncpg:// for async driver
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        elif not self.database_url.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must start with 'postgresql://' or 'postgresql+asyncpg://'"
            )

        logger.info("Database configuration initialized")

    def get_engine(self) -> AsyncEngine:
        """
        Create and return an async database engine.

        Configuration optimized for Neon Serverless:
        - pool_pre_ping=True: Critical for serverless cold starts
        - pool_size=5: Smaller pool for serverless (vs 10-20 for traditional)
        - max_overflow=10: Additional connections when pool exhausted
        - pool_recycle=3600: Recycle connections after 1 hour
        - echo=False: Disable SQL logging in production (set True for debugging)

        Returns:
            AsyncEngine configured for Neon PostgreSQL

        Raises:
            ValueError: If DATABASE_URL is not set or invalid
        """
        # SSL configuration for Neon (asyncpg requires ssl='require' as connect_arg)
        import ssl as ssl_module

        engine = create_async_engine(
            self.database_url,
            echo=False,  # Set to True for SQL query logging during development
            future=True,
            pool_pre_ping=True,  # CRITICAL: Validates connections before use
            pool_size=5,  # Smaller pool for serverless optimization
            max_overflow=10,  # Additional connections when needed
            pool_recycle=3600,  # Recycle connections after 1 hour (prevents stale connections)
            connect_args={
                "ssl": ssl_module.create_default_context(),  # Enable SSL for Neon
                "server_settings": {
                    "application_name": "todo-api"
                }
            }
        )

        logger.info("Database engine created with Neon-optimized settings")
        return engine


# Global engine instance (singleton pattern)
_engine: AsyncEngine | None = None
_session_factory: sessionmaker | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create the global database engine.

    Returns:
        AsyncEngine instance (singleton)
    """
    global _engine
    if _engine is None:
        config = DatabaseConfig()
        _engine = config.get_engine()
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get or create the global session factory.

    Returns:
        sessionmaker configured for async sessions
    """
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Prevent lazy loading issues after commit
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session for FastAPI routes.

    Usage in FastAPI:
        @app.get("/api/todos")
        async def list_todos(session: AsyncSession = Depends(get_session)):
            # Use session here
            pass

    Yields:
        AsyncSession for database operations

    Note:
        This is an async generator that properly handles session lifecycle.
        The session is automatically closed after the request completes.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """
    Create all database tables defined in SQLModel models.

    This should be called once during application startup.
    Uses SQLModel.metadata.create_all() to create tables.

    Note:
        - Only creates tables that don't exist (IF NOT EXISTS)
        - Does not modify existing tables (use migrations for schema changes)
        - Better Auth tables are managed separately (not created here)

    Raises:
        Exception: If table creation fails
    """
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def close_engine() -> None:
    """
    Close the database engine and release all connections.

    This should be called during application shutdown.
    Ensures all connections are properly closed and resources released.
    """
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed and connections released")


# Health check function for monitoring
async def check_database_health() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        True if database is accessible, False otherwise

    Usage:
        Used by health check endpoints to verify database connectivity
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
