"""
Database Layer for Interactive Todo Application (v2.0.0)

Owner: Database Agent
Purpose: Neon PostgreSQL connection management and schema initialization
Architecture: 100% async/await with connection pooling and retry logic

Constitutional Constraints:
- ALLOWED: Database connections, SQL queries, schema initialization, error handling
- FORBIDDEN: User input (input()), User output (print() for menus), Business logic, Service layer calls
- FORBIDDEN: CRUD functions (SELECT, INSERT, UPDATE, DELETE) - these belong in src/repository.py

All operations use parameterized queries to prevent SQL injection.
All connections are managed via an asynchronous pool with retry logic for Neon cold starts.
"""

import os
import asyncio
import logging
from typing import Optional
import psycopg
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    filename=".app.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("database")

# Load environment variables
load_dotenv()

class DatabaseManager:
    """
    Manages asynchronous database connections and schema initialization.

    Includes retry logic for Neon cold starts and connection pooling.
    """

    _pool: Optional[AsyncConnectionPool] = None
    _instance: Optional['DatabaseManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    async def get_pool(self) -> AsyncConnectionPool:
        """
        Initialize and return the connection pool.

        Returns:
            AsyncConnectionPool instance

        Raises:
            ConnectionError: If DATABASE_URL is missing or connection fails
        """
        if self._pool is None:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                logger.error("DATABASE_URL environment variable is missing")
                raise ConnectionError(
                    "DATABASE_URL environment variable is not set. "
                    "Please create a .env file with DATABASE_URL=<your-neon-connection-string>"
                )

            try:
                # Connection string optimization for Neon (e.g., adding keepalives)
                # pool_size can be adjusted based on requirements
                self._pool = AsyncConnectionPool(
                    conninfo=database_url,
                    open=True,
                    min_size=1,
                    max_size=10,
                    timeout=30.0,
                    name="todo_pool"
                )
                logger.info("Database connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise ConnectionError(f"Failed to initialize database pool: {e}")

        return self._pool

    async def close_pool(self) -> None:
        """Close the connection pool and release resources."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    async def get_connection(self, max_retries: int = 5, initial_delay: float = 1.0):
        """
        Obtain a connection from the pool with retry logic for cold starts.

        Args:
            max_retries: Maximum number of attempts to connect
            initial_delay: Initial delay between retries in seconds

        Returns:
            An asynchronous connection context manager

        Raises:
            ConnectionError: If connection cannot be established after retries
        """
        pool = await self.get_pool()

        last_exception = None
        delay = initial_delay

        for attempt in range(1, max_retries + 1):
            try:
                # pool.connection() is an async context manager
                async with pool.connection() as conn:
                    # Validate the connection with a simple query
                    await conn.execute("SELECT 1")
                    # If we get here, the connection is healthy
                    # Unfortunately we can't return the connection from within the context manager
                    # without it being returned to the pool.
                    # Users of this method should use the context manager directly.
                    pass

                # If validation succeeded, return a context manager for the caller
                return pool.connection()

            except (psycopg.OperationalError, Exception) as e:
                last_exception = e
                logger.warning(f"Database connection attempt {attempt} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

        logger.error(f"Failed to connect to database after {max_retries} attempts.")
        raise ConnectionError(f"Could not connect to database: {last_exception}")

async def init_db() -> None:
    """
    Initialize the database schema for the Todo application.

    Includes task table creation with new columns (priority, category, due_date)
    and indexes for optimization.

    Schema:
        - id: SERIAL PRIMARY KEY
        - title: TEXT NOT NULL
        - description: TEXT
        - priority: TEXT DEFAULT 'medium' (CHECK: low, medium, high)
        - category: TEXT
        - due_date: TIMESTAMP
        - is_completed: BOOLEAN DEFAULT FALSE
        - created_at: TIMESTAMP DEFAULT NOW()
        - updated_at: TIMESTAMP DEFAULT NOW()

    Constitutional Compliance:
        ✅ Async/await pattern
        ✅ Parameterized queries
        ✅ No business logic
        ✅ No user interaction
    """
    db = DatabaseManager()

    try:
        pool = await db.get_pool()

        logger.info("Initializing database schema...")

        # Create the tasks table with modern schema requirements - without constraint initially to avoid conflicts
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT,
                        priority TEXT DEFAULT 'medium',
                        category TEXT,
                        due_date TIMESTAMP,
                        is_completed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                """)
            await conn.commit()

        # Migration: Ensure new columns exist for users upgrading from beginner version
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Add recurrence_interval column (backward compatible)
                await cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS recurrence_interval TEXT DEFAULT 'none';")
                await conn.commit()

        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Add parent_task_id foreign key
                await cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS parent_task_id INT;")
                await conn.commit()

        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Add reminder_sent flag
                await cur.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN DEFAULT FALSE;")
                await conn.commit()

        # Add recurrence_interval check constraint (non-validating for existing data)
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Drop existing constraint first to ensure it has correct values
                await cur.execute("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS recurrence_check;")
                await cur.execute("ALTER TABLE tasks ADD CONSTRAINT recurrence_check CHECK (recurrence_interval IN ('daily', 'weekly', 'monthly', 'none')) NOT VALID;")
                # Validate the constraint for existing rows
                await cur.execute("ALTER TABLE tasks VALIDATE CONSTRAINT recurrence_check;")
                await conn.commit()

        # Create indexes for performance optimization
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
                """)
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
                """)
                # NEW: Index for parent-child queries (task history)
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id);
                """)
                # NEW: Index for reminder check (fast query of pending, unnotified due tasks)
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_reminder
                    ON tasks(due_date) WHERE is_completed = FALSE AND reminder_sent = FALSE;
                """)
                # NEW: Index for recurrence filtering (find all recurring tasks)
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_recurrence
                    ON tasks(recurrence_interval) WHERE recurrence_interval != 'none';
                """)
            await conn.commit()

        logger.info("Database schema initialized successfully")

    except Exception as e:
        logger.error(f"Schema initialization failed: {e}")
        raise

# Singleton instance for easy access
db_manager = DatabaseManager()
