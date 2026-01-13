---
name: mcp-ownership-verification
description: Double-check ownership protocol for MCP tools to verify task.user_id matches before any update or delete operation.
---

# MCP Ownership Verification Protocol

## Overview

This skill defines the mandatory "Double-Check" ownership verification that ALL MCP tools must perform before modifying or deleting user data. This ensures the AI agent cannot be tricked (via prompt injection or other means) into accessing another user's data.

## Core Principle

**CRITICAL**: Before ANY update or delete operation, MCP tools MUST query the database to verify that `task.user_id` matches the `user_id` provided in the tool arguments. This is a second layer of defense beyond route-level authentication.

## Why Double-Check?

1. **Defense in Depth**: Even if a bug passes wrong user_id, the tool catches it
2. **Prompt Injection Protection**: AI cannot be manipulated to access other users' data
3. **Audit Trail**: Failed ownership checks are logged for security review
4. **Consistent Error Messages**: Prevents information leakage about task existence

## Implementation Pattern

### Standard Ownership Check Function

**MUST**: Create a reusable ownership verification function.

```python
# backend/src/mcp/tools/utils.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.task import Task
from typing import Optional

async def verify_task_ownership(
    task_id: int,
    user_id: str,
    session: AsyncSession
) -> Optional[Task]:
    """
    Double-check that task belongs to user before modification.

    Args:
        task_id: The task to verify
        user_id: The user_id from tool arguments (from JWT)
        session: Database session

    Returns:
        Task if ownership verified, None otherwise
    """
    statement = select(Task).where(
        Task.id == task_id,
        Task.user_id == user_id  # ✅ CRITICAL: Ownership check
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()
```

### MCP Tool: complete_task

**MUST**: Verify ownership before marking task complete.

```python
# backend/src/mcp/tools/task_tools.py
from mcp import tool
from typing import Annotated

@tool
async def complete_task(
    user_id: Annotated[str, "The authenticated user's ID from JWT"],
    task_id: Annotated[int, "The ID of the task to complete"],
    session: AsyncSession
) -> str:
    """
    Mark a task as complete.

    Performs ownership double-check before modification.
    """
    # ✅ CRITICAL: Double-check ownership
    task = await verify_task_ownership(task_id, user_id, session)

    if not task:
        # ✅ REQUIRED: Standard error message (no info leakage)
        return "Error: Task not found or unauthorized"

    # Ownership verified - safe to modify
    task.is_completed = True
    task.updated_at = datetime.utcnow()
    await session.commit()

    return f"Task '{task.title}' marked as complete."
```

### MCP Tool: update_task

**MUST**: Verify ownership before updating task.

```python
@tool
async def update_task(
    user_id: Annotated[str, "The authenticated user's ID from JWT"],
    task_id: Annotated[int, "The ID of the task to update"],
    title: Annotated[str, "New title for the task"] = None,
    description: Annotated[str, "New description for the task"] = None,
    session: AsyncSession = None
) -> str:
    """
    Update a task's title or description.

    Performs ownership double-check before modification.
    """
    # ✅ CRITICAL: Double-check ownership
    task = await verify_task_ownership(task_id, user_id, session)

    if not task:
        # ✅ REQUIRED: Standard error message
        return "Error: Task not found or unauthorized"

    # Ownership verified - safe to modify
    if title:
        task.title = title
    if description:
        task.description = description
    task.updated_at = datetime.utcnow()

    await session.commit()

    return f"Task '{task.title}' updated successfully."
```

### MCP Tool: delete_task

**MUST**: Verify ownership before deleting task.

```python
@tool
async def delete_task(
    user_id: Annotated[str, "The authenticated user's ID from JWT"],
    task_id: Annotated[int, "The ID of the task to delete"],
    session: AsyncSession = None
) -> str:
    """
    Delete a task.

    Performs ownership double-check before deletion.
    """
    # ✅ CRITICAL: Double-check ownership
    task = await verify_task_ownership(task_id, user_id, session)

    if not task:
        # ✅ REQUIRED: Standard error message
        return "Error: Task not found or unauthorized"

    # Ownership verified - safe to delete
    task_title = task.title
    await session.delete(task)
    await session.commit()

    return f"Task '{task_title}' deleted successfully."
```

### MCP Tool: add_task (No Double-Check Needed)

**NOTE**: Create operations don't need ownership verification - they assign ownership.

```python
@tool
async def add_task(
    user_id: Annotated[str, "The authenticated user's ID from JWT"],
    title: Annotated[str, "Title of the new task"],
    description: Annotated[str, "Optional description"] = None,
    session: AsyncSession = None
) -> str:
    """
    Create a new task for the user.

    No ownership check needed - task is created with user_id.
    """
    task = Task(
        user_id=user_id,  # ✅ Assign ownership at creation
        title=title,
        description=description,
        is_completed=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(task)
    await session.commit()
    await session.refresh(task)

    return f"Task '{title}' added with ID {task.id}."
```

### MCP Tool: list_tasks (Filter, Don't Double-Check)

**NOTE**: List operations filter by user_id - no individual ownership check needed.

```python
@tool
async def list_tasks(
    user_id: Annotated[str, "The authenticated user's ID from JWT"],
    status: Annotated[str, "Filter: 'all', 'completed', or 'pending'"] = "all",
    session: AsyncSession = None
) -> str:
    """
    List user's tasks with optional status filter.

    Filters by user_id - only returns user's own tasks.
    """
    statement = select(Task).where(Task.user_id == user_id)  # ✅ Filter by user

    if status == "completed":
        statement = statement.where(Task.is_completed == True)
    elif status == "pending":
        statement = statement.where(Task.is_completed == False)

    result = await session.execute(statement)
    tasks = result.scalars().all()

    if not tasks:
        return "You have no tasks."

    task_list = "\n".join([
        f"- [{task.id}] {'✓' if task.is_completed else '○'} {task.title}"
        for task in tasks
    ])

    return f"Your tasks:\n{task_list}"
```

## Error Message Standard

**MUST**: Always return the same error message for both "not found" and "unauthorized".

```python
# ✅ CORRECT: Single message prevents information leakage
return "Error: Task not found or unauthorized"

# ❌ WRONG: Reveals task exists but belongs to another user
return "Error: You don't have permission to access this task"

# ❌ WRONG: Reveals task doesn't exist
return "Error: Task not found"
```

**Why**: Different error messages allow attackers to enumerate which task IDs exist.

## Logging Failed Checks

**SHOULD**: Log ownership verification failures for security monitoring.

```python
import logging

logger = logging.getLogger(__name__)

async def verify_task_ownership(
    task_id: int,
    user_id: str,
    session: AsyncSession
) -> Optional[Task]:
    """Verify ownership with security logging"""
    statement = select(Task).where(
        Task.id == task_id,
        Task.user_id == user_id
    )
    result = await session.execute(statement)
    task = result.scalar_one_or_none()

    if not task:
        # Log for security monitoring (potential attack or bug)
        logger.warning(
            f"Ownership check failed: task_id={task_id}, user_id={user_id}"
        )

    return task
```

## When to Double-Check

| Operation | Double-Check Required? | Reason |
|-----------|----------------------|--------|
| `add_task` | No | Creates with user_id |
| `list_tasks` | No | Filters by user_id |
| `get_task` | Yes | Returns specific task |
| `update_task` | **Yes** | Modifies existing task |
| `complete_task` | **Yes** | Modifies existing task |
| `delete_task` | **Yes** | Removes existing task |

## Security Checklist

- [ ] All update tools verify ownership before modification
- [ ] All delete tools verify ownership before deletion
- [ ] Error message is always "Task not found or unauthorized"
- [ ] No different messages for "not found" vs "unauthorized"
- [ ] Failed ownership checks are logged
- [ ] user_id comes from JWT (not user input)
- [ ] Ownership check uses AND condition (id AND user_id)

## Testing

```python
# backend/tests/test_mcp_ownership.py
import pytest

@pytest.mark.asyncio
async def test_complete_task_wrong_user():
    """Verify complete_task rejects wrong user"""
    # Create task for user_a
    task = await create_task(user_id="user_a", title="Test")

    # Attempt to complete as user_b
    result = await complete_task(
        user_id="user_b",
        task_id=task.id,
        session=db_session
    )

    assert result == "Error: Task not found or unauthorized"
    # Verify task unchanged
    assert not task.is_completed

@pytest.mark.asyncio
async def test_delete_task_wrong_user():
    """Verify delete_task rejects wrong user"""
    task = await create_task(user_id="user_a", title="Test")

    result = await delete_task(
        user_id="user_b",
        task_id=task.id,
        session=db_session
    )

    assert result == "Error: Task not found or unauthorized"
    # Verify task still exists
    assert await get_task(task.id) is not None

@pytest.mark.asyncio
async def test_complete_task_correct_user():
    """Verify complete_task works for correct user"""
    task = await create_task(user_id="user_a", title="Test")

    result = await complete_task(
        user_id="user_a",
        task_id=task.id,
        session=db_session
    )

    assert "marked as complete" in result
    assert task.is_completed
```

## References

- Constitution Principle IV: Security: User Isolation
- Constitution Principle VII: Tool-Only AI Access (MCP)
- neon-tenant-isolation skill: Database query patterns
