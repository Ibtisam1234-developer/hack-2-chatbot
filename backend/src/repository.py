"""
Repository Layer for Interactive Todo Application (v2.0.0)

Owner: Database Agent
Purpose: Data persistence and retrieval logic for tasks
Architecture: Async/Await with PostgreSQL using psycopg3

Constitutional Constraints:
- ALLOWED: CRUD operations, SQL queries, parameterized inputs, async implementation
- FORBIDDEN: User interaction (input/print), direct database connections (must use database.py),
             business logic validation, UI formatting.

All functions use full column sets to remain consistent with Task.from_db_row.
"""

import logging
from typing import List, Optional, Any
from datetime import datetime
from src.database import db_manager
from src.models import Task, Priority, TaskStatus

logger = logging.getLogger("repository")

# Full column set to ensure consistency across all SELECT queries
FULL_COLUMN_SET = (
    "id, title, description, priority, category, due_date, "
    "is_completed, recurrence_interval, parent_task_id, "
    "reminder_sent, created_at, updated_at"
)

async def create_task(title: str, description: Optional[str] = None,
                priority: str = 'medium', category: Optional[str] = None,
                due_date: Optional[datetime] = None,
                recurrence_interval: str = 'none',
                parent_task_id: Optional[int] = None) -> Task:
    """
    Create a new task in the database.

    Args:
        title: Task title
        description: Optional description
        priority: Task priority (low, medium, high)
        category: Optional category
        due_date: Optional due date
        recurrence_interval: Recurrence interval (daily, weekly, monthly, none)
        parent_task_id: Optional parent task ID

    Returns:
        The newly created Task object
    """
    async with await db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                INSERT INTO tasks (title, description, priority, category, due_date,
                                recurrence_interval, parent_task_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING {FULL_COLUMN_SET}
                """,
                (title, description, priority, category, due_date,
                 recurrence_interval, parent_task_id)
            )
            row = await cur.fetchone()
            await conn.commit()

            # row: (id, title, description, priority, category, due_date,
            #      is_completed, recurrence_interval, parent_task_id,
            #      reminder_sent, created_at, updated_at)
            # models.Task.from_db_row expects this exact order and content
            return Task.from_db_row(row)

async def get_all_tasks(status: Optional[str] = None,
                   category: Optional[str] = None,
                   priority: Optional[str] = None,
                   parent_task_id: Optional[int] = None,
                   recurrence_interval: Optional[str] = None,
                   due_before: Optional[datetime] = None,
                   due_after: Optional[datetime] = None,
                   sort_by: str = 'date') -> List[Task]:
    """
    Retrieve all tasks with optional filters and sorting.

    Args:
        status: Filter by completion status ('completed', 'pending')
        category: Filter by category
        priority: Filter by priority
        parent_task_id: Filter by parent task (for task history)
        recurrence_interval: Filter by recurrence interval
        due_before: Filter by due date before this time
        due_after: Filter by due date after this time
        sort_by: Sorting method ('date', 'alpha', 'priority')

    Returns:
        List of Task objects
    """
    query = f"SELECT {FULL_COLUMN_SET} FROM tasks"
    conditions = []
    params = []

    if status == 'completed':
        conditions.append("is_completed = TRUE")
    elif status == 'pending':
        conditions.append("is_completed = FALSE")

    if category:
        conditions.append("category = %s")
        params.append(category)

    if priority:
        conditions.append("priority = %s")
        params.append(priority)

    if parent_task_id:
        conditions.append("parent_task_id = %s")
        params.append(parent_task_id)

    if recurrence_interval:
        conditions.append("recurrence_interval = %s")
        params.append(recurrence_interval)

    if due_before:
        conditions.append("due_date <= %s")
        params.append(due_before)

    if due_after:
        conditions.append("due_date >= %s")
        params.append(due_after)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Sorting logic
    if sort_by == 'priority':
        query += """ ORDER BY CASE
            WHEN priority = 'high' THEN 1
            WHEN priority = 'medium' THEN 2
            WHEN priority = 'low' THEN 3
            ELSE 4 END, created_at DESC"""
    elif sort_by == 'alpha':
        query += ' ORDER BY title COLLATE "C" ASC'
    else:  # default 'date'
        query += " ORDER BY due_date ASC NULLS LAST, created_at DESC"

    async with await db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            rows = await cur.fetchall()
            return [Task.from_db_row(row) for row in rows]

async def update_task(task_id: int, **kwargs) -> Optional[Task]:
    """
    Update an existing task.

    Args:
        task_id: ID of the task to update
        **kwargs: Fields to update (title, description, priority, category, due_date, is_completed, recurrence_interval, parent_task_id, reminder_sent)

    Returns:
        Updated Task object or None if not found
    """
    # handle reminder_sent reset on due_date change
    if 'due_date' in kwargs and 'reminder_sent' not in kwargs:
        kwargs['reminder_sent'] = False

    # Filter out None values or handle specific field mapping if necessary
    # is_completed might be passed instead of status based on previous implementation
    if 'status' in kwargs and 'is_completed' not in kwargs:
        kwargs['is_completed'] = (kwargs.pop('status') == TaskStatus.COMPLETED)

    # Only keep non-None values to avoid updating with NULL where not allowed
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    if not kwargs:
        return await get_task_by_id(task_id)

    kwargs['updated_at'] = datetime.now()

    # Use parameterized query for security
    columns = []
    params = []
    for k, v in kwargs.items():
        columns.append(f"{k} = %s")
        params.append(v)

    set_clause = ", ".join(columns)
    params.append(task_id)

    query = f"UPDATE tasks SET {set_clause} WHERE id = %s RETURNING {FULL_COLUMN_SET}"

    async with await db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            row = await cur.fetchone()
            await conn.commit()
            if row:
                return Task.from_db_row(row)
            return None

async def delete_task(task_id: int) -> bool:
    """
    Delete a task from the database.

    Args:
        task_id: ID of the task to delete

    Returns:
        True if deleted, False otherwise
    """
    async with await db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            result = cur.rowcount > 0
            await conn.commit()
            return result

async def search_tasks(query: str) -> List[Task]:
    """
    Search for tasks by title or description.

    Args:
        query: Search string

    Returns:
        List of matching Task objects
    """
    search_term = f"%{query}%"
    sql = f"""
        SELECT {FULL_COLUMN_SET}
        FROM tasks
        WHERE title ILIKE %s OR description ILIKE %s
        ORDER BY created_at DESC
    """
    async with await db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (search_term, search_term))
            rows = await cur.fetchall()
            return [Task.from_db_row(row) for row in rows]

async def get_task_by_id(task_id: int) -> Optional[Task]:
    """
    Retrieve a single task by ID.

    Args:
        task_id: Task ID

    Returns:
        Task object or None if not found
    """
    async with await db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT {FULL_COLUMN_SET} FROM tasks WHERE id = %s",
                (task_id,)
            )
            row = await cur.fetchone()
            if row:
                return Task.from_db_row(row)
            return None

async def get_task_history(root_task_id: int) -> List[Task]:
    """
    Get all instances of a recurring task series.

    Args:
        root_task_id: ID of the root task

    Returns:
        List of Task objects in the series
    """
    async with await db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            # Query: root task OR any task with parent_task_id = root_task_id
            query = f"""
                SELECT {FULL_COLUMN_SET}
                FROM tasks
                WHERE id = %s OR parent_task_id = %s
                ORDER BY created_at ASC
            """
            await cur.execute(query, (root_task_id, root_task_id))
            rows = await cur.fetchall()
            return [Task.from_db_row(row) for row in rows]
