"""
Database Package Initialization for Todo API

Owner: Database Reliability Engineer
Purpose: Central database module exports and initialization
Architecture: Async/await with SQLModel and Neon PostgreSQL

This module provides:
- Database connection management (get_session, get_engine)
- SQLModel models (Todo, TodoCreate, TodoUpdate, TodoResponse)
- Initialization utilities (create_tables, init_database)
- Health check functions

Usage:
    from backend.src.db import get_session, Todo, TodoCreate
    from backend.src.db import init_database

    # Initialize database on startup
    await init_database()

    # Use in FastAPI routes
    @app.get("/api/todos")
    async def list_todos(session: AsyncSession = Depends(get_session)):
        # Query todos with user isolation
        pass
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy import text

# Import connection utilities
from .connection import (
    get_engine,
    get_session,
    get_session_factory,
    create_tables,
    close_engine,
    check_database_health,
)

# Import models
from .models import (
    Todo,
    TodoBase,
    TodoCreate,
    TodoUpdate,
    TodoResponse,
)

# Import chat models (Phase III)
from ..models.conversation import Conversation
from ..models.message import Message

# Configure logging
logger = logging.getLogger("database")


async def init_database() -> None:
    """
    Initialize the database for the Todo API.

    This function should be called once during application startup.

    Steps:
    1. Create all SQLModel tables (todos table)
    2. Create composite index for query optimization
    3. Verify database connectivity

    Note:
    - Better Auth tables are managed separately (not created here)
    - Only creates tables that don't exist (IF NOT EXISTS)
    - Safe to call multiple times (idempotent)

    Raises:
        Exception: If database initialization fails
    """
    logger.info("Initializing database for Todo API...")

    try:
        # Step 1: Create all SQLModel tables
        await create_tables()
        logger.info("✓ Database tables created")

        # Step 2: Create composite index for optimized queries
        # Index: (user_id, is_completed) for "show my incomplete todos" queries
        engine = get_engine()
        async with engine.begin() as conn:
            # Check if index exists before creating
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_todos_user_completed
                ON todos(user_id, is_completed);
            """))
        logger.info("✓ Composite index created (user_id, is_completed)")

        # Step 3: Verify database connectivity
        is_healthy = await check_database_health()
        if not is_healthy:
            raise ConnectionError("Database health check failed")
        logger.info("✓ Database health check passed")

        logger.info("Database initialization complete")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def cleanup_database() -> None:
    """
    Cleanup database connections during application shutdown.

    This function should be called during application shutdown to:
    - Close all database connections
    - Release connection pool resources
    - Ensure graceful shutdown

    Usage:
        @app.on_event("shutdown")
        async def shutdown():
            await cleanup_database()
    """
    logger.info("Cleaning up database connections...")
    await close_engine()
    logger.info("Database cleanup complete")


# Export all public components
__all__ = [
    # Connection utilities
    "get_engine",
    "get_session",
    "get_session_factory",
    "create_tables",
    "close_engine",
    "check_database_health",
    # Models
    "Todo",
    "TodoBase",
    "TodoCreate",
    "TodoUpdate",
    "TodoResponse",
    # Chat models (Phase III)
    "Conversation",
    "Message",
    # Initialization
    "init_database",
    "cleanup_database",
]
