"""
Migration script to add category and due_date columns to todos table.

This script adds the missing columns that were added to the SQLModel
but don't exist in the database yet.
"""

import asyncio
from sqlalchemy import text
from src.db.connection import get_engine


async def migrate():
    """Add category and due_date columns to todos table."""
    engine = get_engine()

    async with engine.begin() as conn:
        print("Adding category column...")
        try:
            await conn.execute(text(
                "ALTER TABLE todos ADD COLUMN IF NOT EXISTS category VARCHAR(50)"
            ))
            print("✓ Category column added")
        except Exception as e:
            print(f"Category column: {e}")

        print("Adding due_date column...")
        try:
            await conn.execute(text(
                "ALTER TABLE todos ADD COLUMN IF NOT EXISTS due_date TIMESTAMP"
            ))
            print("✓ Due_date column added")
        except Exception as e:
            print(f"Due_date column: {e}")

        print("\nMigration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())
