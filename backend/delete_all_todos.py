"""
Script to delete all todos from the database.
Use this to clear the database for testing.
"""

import asyncio
from sqlalchemy import text
from src.db.connection import get_engine


async def delete_all_todos():
    """Delete all todos from the database."""
    engine = get_engine()

    async with engine.begin() as conn:
        print("Deleting all todos...")
        result = await conn.execute(text("DELETE FROM todos"))
        print(f"Deleted {result.rowcount} todos")
        print("\nDatabase cleared successfully!")


if __name__ == "__main__":
    asyncio.run(delete_all_todos())
