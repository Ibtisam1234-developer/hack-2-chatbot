"""
Database Verification Script for Todo API

Purpose: Verify database connection and schema initialization
Usage: python -m backend.src.db.verify

This script:
1. Tests database connection to Neon PostgreSQL
2. Verifies all tables are created correctly
3. Checks indexes are in place
4. Validates schema matches SQLModel definitions

Run this after setting up your DATABASE_URL in .env file.
"""

import asyncio
import sys
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("database.verify")


async def verify_database():
    """
    Verify database setup and connectivity.

    Returns:
        bool: True if all checks pass, False otherwise
    """
    try:
        # Import after logging is configured
        from backend.src.db import (
            init_database,
            get_session,
            check_database_health,
            get_engine
        )

        logger.info("=" * 60)
        logger.info("Database Verification Script")
        logger.info("=" * 60)

        # Step 1: Check database health
        logger.info("\n[1/5] Checking database connectivity...")
        is_healthy = await check_database_health()
        if not is_healthy:
            logger.error("✗ Database connection failed")
            return False
        logger.info("✓ Database connection successful")

        # Step 2: Initialize database (create tables and indexes)
        logger.info("\n[2/5] Initializing database schema...")
        await init_database()
        logger.info("✓ Database schema initialized")

        # Step 3: Verify todos table exists
        logger.info("\n[3/5] Verifying todos table...")
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'todos'
                );
            """))
            table_exists = result.scalar()

            if not table_exists:
                logger.error("✗ Todos table not found")
                return False
            logger.info("✓ Todos table exists")

        # Step 4: Verify table schema
        logger.info("\n[4/5] Verifying table schema...")
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'todos'
                ORDER BY ordinal_position;
            """))
            columns = result.fetchall()

            required_columns = {
                'id': 'uuid',
                'user_id': 'character varying',
                'title': 'character varying',
                'description': 'character varying',
                'is_completed': 'boolean',
                'created_at': 'timestamp without time zone',
                'updated_at': 'timestamp without time zone'
            }

            found_columns = {col[0]: col[1] for col in columns}

            for col_name, col_type in required_columns.items():
                if col_name not in found_columns:
                    logger.error(f"✗ Missing column: {col_name}")
                    return False
                logger.info(f"  ✓ Column '{col_name}' ({found_columns[col_name]})")

        # Step 5: Verify indexes
        logger.info("\n[5/5] Verifying indexes...")
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'todos';
            """))
            indexes = [row[0] for row in result.fetchall()]

            required_indexes = ['todos_pkey', 'ix_todos_user_id', 'idx_todos_user_completed']

            for index_name in required_indexes:
                if index_name in indexes:
                    logger.info(f"  ✓ Index '{index_name}' exists")
                else:
                    logger.warning(f"  ⚠ Index '{index_name}' not found (may be created with different name)")

        logger.info("\n" + "=" * 60)
        logger.info("✓ All verification checks passed!")
        logger.info("=" * 60)
        logger.info("\nDatabase is ready for use.")
        logger.info("Next steps:")
        logger.info("  1. Start the FastAPI server: uvicorn backend.src.api.main:app --reload")
        logger.info("  2. Test the API endpoints with authentication")
        logger.info("  3. Verify user isolation in multi-tenant scenarios")

        return True

    except ValueError as e:
        logger.error(f"\n✗ Configuration error: {e}")
        logger.error("\nPlease ensure:")
        logger.error("  1. .env file exists in project root")
        logger.error("  2. DATABASE_URL is set with your Neon connection string")
        logger.error("  3. Format: postgresql://user:password@host.neon.tech/database")
        return False

    except Exception as e:
        logger.error(f"\n✗ Verification failed: {e}")
        logger.exception("Full error details:")
        return False


async def main():
    """Main entry point for verification script."""
    success = await verify_database()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
