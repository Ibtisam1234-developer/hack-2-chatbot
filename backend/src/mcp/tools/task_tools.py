# backend/src/mcp/tools/task_tools.py
"""
MCP Tools for AI Chatbot Task Management

Owner: MCP Engineer
Purpose: Tool definitions for AI agent task operations
Architecture: FastMCP tools with async database operations

Constitutional Constraints:
- REQUIRED: All tools enforce user_id isolation (Principle IV)
- REQUIRED: Tools are the ONLY way AI accesses data (Principle VII)
- REQUIRED: Ownership double-check before modifications (mcp-ownership-verification)

Note: Core functions are defined separately from MCP decorators to allow
direct calling from the chat endpoint while also exposing them via MCP.
"""

import logging
from typing import Annotated, Optional
from uuid import UUID
from fastmcp import FastMCP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from src.db.connection import get_session_factory
from src.db.models import Todo

logger = logging.getLogger("mcp.tools.task_tools")

# Initialize FastMCP server
mcp = FastMCP("task-tools")


async def find_task_by_short_id(
    short_id: str,
    user_id: str,
    session: AsyncSession
) -> Todo | None:
    """
    Find a task by short ID (first 8 chars of UUID).

    Uses raw SQL since SQLAlchemy UUID cast doesn't work well.
    """
    # Use raw SQL for the LIKE query on UUID
    query = text("""
        SELECT id, user_id, title, description, is_completed, created_at, updated_at
        FROM todo
        WHERE user_id = :user_id AND CAST(id AS TEXT) LIKE :pattern
        LIMIT 1
    """)
    result = await session.execute(query, {"user_id": user_id, "pattern": f"{short_id}%"})
    row = result.fetchone()

    if row:
        # Fetch the actual ORM object
        statement = select(Todo).where(Todo.id == row[0], Todo.user_id == user_id)
        orm_result = await session.execute(statement)
        return orm_result.scalar_one_or_none()
    return None


async def verify_task_ownership(
    task_id: str,
    user_id: str,
    session: AsyncSession
) -> Todo | None:
    """
    Double-check ownership before modification.

    Per mcp-ownership-verification skill:
    - Always verify task.user_id matches the authenticated user_id
    - Return None if task doesn't exist OR user doesn't own it
    - Error message must not reveal whether task exists for other users

    Args:
        task_id: UUID string of the task
        user_id: Authenticated user's ID from JWT sub claim
        session: Active database session

    Returns:
        Todo if found and owned by user, None otherwise
    """
    try:
        uuid_id = UUID(task_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for task_id: {task_id}")
        return None

    statement = select(Todo).where(
        Todo.id == uuid_id,
        Todo.user_id == user_id
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


# ============================================================================
# Core tool functions (directly callable)
# ============================================================================

async def add_task_impl(
    user_id: str,
    title: str,
    description: Optional[str] = None
) -> str:
    """Create a new task for the user."""
    # Validate title
    if not title or not title.strip():
        return "Error: Title is required and cannot be empty."

    if len(title) > 200:
        return "Error: Title must be 200 characters or less."

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            task = Todo(
                user_id=user_id,
                title=title.strip(),
                description=description,
                is_completed=False
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)

            logger.info(f"Task created: {task.id} for user {user_id}")
            return f"Task '{task.title}' added with ID {task.id}."
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create task: {e}")
            return "Error: Failed to create task. Please try again."


async def list_tasks_impl(
    user_id: str,
    status: str = "all"
) -> str:
    """List the user's tasks with optional status filter."""
    # Validate status
    valid_statuses = ["all", "pending", "completed"]
    if status not in valid_statuses:
        return f"Error: Invalid status '{status}'. Use 'all', 'pending', or 'completed'."

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            statement = select(Todo).where(Todo.user_id == user_id)

            if status == "pending":
                statement = statement.where(Todo.is_completed == False)
            elif status == "completed":
                statement = statement.where(Todo.is_completed == True)

            statement = statement.order_by(Todo.created_at.desc())
            result = await session.execute(statement)
            tasks = result.scalars().all()

            if not tasks:
                return "You have no tasks."

            status_label = f"{status} " if status != "all" else ""
            lines = [f"Your {status_label}tasks:"]
            for task in tasks:
                icon = "[x]" if task.is_completed else "[ ]"
                # Show full UUID for clarity
                lines.append(f"- ID: {task.id} {icon} {task.title}")

            logger.info(f"Listed {len(tasks)} tasks for user {user_id}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return "Error: Failed to retrieve tasks. Please try again."


async def complete_task_impl(
    user_id: str,
    task_id: str
) -> str:
    """Mark a task as complete. Verifies ownership before modification."""
    # Validate task_id is provided
    if not task_id or not task_id.strip():
        return "Error: Task ID is required. Please use 'show my tasks' to see your tasks with their IDs."

    task_id = task_id.strip()

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            # Handle short ID (first 8 chars) or full UUID
            if len(task_id) == 8:
                logger.info(f"Using short ID search for task_id: {task_id}")
                task = await find_task_by_short_id(task_id, user_id, session)
            else:
                logger.info(f"Using full UUID search for task_id: {task_id}")
                task = await verify_task_ownership(task_id, user_id, session)

            if not task:
                return f"Error: Task with ID '{task_id}' not found. Please check the ID and try again."

            if task.is_completed:
                return f"Task '{task.title}' is already complete."

            task.is_completed = True
            await session.commit()

            logger.info(f"Task completed: {task.id} for user {user_id}")
            return f"Task '{task.title}' marked as complete."
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to complete task: {e}")
            return "Error: Failed to complete task. Please try again."


async def update_task_impl(
    user_id: str,
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """Update a task's title or description. Verifies ownership before modification."""
    logger.info(f"update_task_impl called: user_id={user_id}, task_id={task_id}, title={title}, description={description}")

    # Validate task_id is provided
    if not task_id or not task_id.strip():
        return "Error: Task ID is required. Please use 'show my tasks' to see your tasks with their IDs."

    task_id = task_id.strip()

    if not title and description is None:
        return "Error: Provide at least a new title or description to update."

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            # Handle short ID (first 8 chars) or full UUID
            if len(task_id) == 8:
                logger.info(f"Using short ID search for task_id: {task_id}")
                task = await find_task_by_short_id(task_id, user_id, session)
            else:
                logger.info(f"Using full UUID search for task_id: {task_id}")
                task = await verify_task_ownership(task_id, user_id, session)

            if not task:
                logger.warning(f"Task not found or unauthorized: task_id={task_id}, user_id={user_id}")
                return f"Error: Task with ID '{task_id}' not found. Please check the ID and try again."

            old_title = task.title
            if title:
                if len(title) > 200:
                    return "Error: Title must be 200 characters or less."
                task.title = title.strip()
            if description is not None:
                task.description = description

            await session.commit()

            logger.info(f"Task updated: {task.id} for user {user_id}")
            return f"Task updated: '{old_title}' -> '{task.title}'"
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update task: {e}")
            return "Error: Failed to update task. Please try again."


async def delete_task_impl(
    user_id: str,
    task_id: str
) -> str:
    """Delete a task. Verifies ownership before deletion."""
    # Validate task_id is provided
    if not task_id or not task_id.strip():
        return "Error: Task ID is required. Please use 'show my tasks' to see your tasks with their IDs."

    task_id = task_id.strip()

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            # Handle short ID (first 8 chars) or full UUID
            if len(task_id) == 8:
                logger.info(f"Using short ID search for task_id: {task_id}")
                task = await find_task_by_short_id(task_id, user_id, session)
            else:
                logger.info(f"Using full UUID search for task_id: {task_id}")
                task = await verify_task_ownership(task_id, user_id, session)

            if not task:
                return f"Error: Task with ID '{task_id}' not found. Please check the ID and try again."

            task_title = task.title
            await session.delete(task)
            await session.commit()

            logger.info(f"Task deleted: {task_id} for user {user_id}")
            return f"Task '{task_title}' has been deleted."
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to delete task: {e}")
            return "Error: Failed to delete task. Please try again."


# ============================================================================
# MCP-decorated wrappers (for MCP server exposure)
# ============================================================================

@mcp.tool()
async def add_task(
    user_id: Annotated[str, "The authenticated user's ID from JWT sub claim"],
    title: Annotated[str, "Title of the task (max 200 characters)"],
    description: Annotated[Optional[str], "Optional description of the task"] = None
) -> str:
    """Create a new task for the user."""
    return await add_task_impl(user_id, title, description)


@mcp.tool()
async def list_tasks(
    user_id: Annotated[str, "The authenticated user's ID from JWT sub claim"],
    status: Annotated[str, "Filter by status: 'all', 'pending', or 'completed'"] = "all"
) -> str:
    """List the user's tasks with optional status filter."""
    return await list_tasks_impl(user_id, status)


@mcp.tool()
async def complete_task(
    user_id: Annotated[str, "The authenticated user's ID from JWT sub claim"],
    task_id: Annotated[str, "The ID (or first 8 characters) of the task to mark as complete"]
) -> str:
    """Mark a task as complete. Verifies ownership before modification."""
    return await complete_task_impl(user_id, task_id)


@mcp.tool()
async def update_task(
    user_id: Annotated[str, "The authenticated user's ID from JWT sub claim"],
    task_id: Annotated[str, "The ID (or first 8 characters) of the task to update"],
    title: Annotated[Optional[str], "New title for the task"] = None,
    description: Annotated[Optional[str], "New description for the task"] = None
) -> str:
    """Update a task's title or description. Verifies ownership before modification."""
    return await update_task_impl(user_id, task_id, title, description)


@mcp.tool()
async def delete_task(
    user_id: Annotated[str, "The authenticated user's ID from JWT sub claim"],
    task_id: Annotated[str, "The ID (or first 8 characters) of the task to delete"]
) -> str:
    """Delete a task. Verifies ownership before deletion."""
    return await delete_task_impl(user_id, task_id)


__all__ = [
    "mcp",
    "add_task", "list_tasks", "complete_task", "update_task", "delete_task",
    "add_task_impl", "list_tasks_impl", "complete_task_impl", "update_task_impl", "delete_task_impl",
    "verify_task_ownership"
]
