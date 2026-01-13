# MCP Tools: AI Chatbot Integration

**Feature**: 002-ai-chatbot
**Date**: 2026-01-11
**Protocol**: Model Context Protocol (MCP)

## Overview

The AI agent interacts with user tasks exclusively through these MCP tools. All tools enforce user isolation via the `user_id` parameter (extracted from JWT `sub` claim) and implement the ownership verification protocol.

## Tool Definitions

### add_task

Creates a new task for the authenticated user.

**Signature**:
```python
@mcp.tool()
async def add_task(
    user_id: Annotated[str, "The authenticated user's ID from JWT sub claim"],
    title: Annotated[str, "Title of the task (max 200 characters)"],
    description: Annotated[str, "Optional description of the task"] = None
) -> str:
    """Create a new task for the user."""
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | string | Yes | User ID from JWT (for ownership) |
| title | string | Yes | Task title (1-200 chars) |
| description | string | No | Optional task description |

**Returns**: Success message with task ID or error string

**Examples**:
```
Input: add_task(user_id="user_123", title="Buy groceries")
Output: "Task 'Buy groceries' added with ID 42."

Input: add_task(user_id="user_123", title="", description="test")
Output: "Error: Title is required and cannot be empty."
```

---

### list_tasks

Lists all tasks for the authenticated user with optional status filter.

**Signature**:
```python
@mcp.tool()
async def list_tasks(
    user_id: Annotated[str, "The authenticated user's ID from JWT sub claim"],
    status: Annotated[str, "Filter by status: 'all', 'pending', or 'completed'"] = "all"
) -> str:
    """List the user's tasks with optional status filter."""
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | string | Yes | User ID from JWT (for isolation) |
| status | string | No | Filter: "all" (default), "pending", "completed" |

**Returns**: Formatted list of tasks or "no tasks" message

**Examples**:
```
Input: list_tasks(user_id="user_123", status="pending")
Output: "Your pending tasks:
- [42] ○ Buy groceries
- [41] ○ Finish report
- [40] ○ Call dentist"

Input: list_tasks(user_id="user_123", status="completed")
Output: "Your completed tasks:
- [39] ✓ Submit timesheet
- [38] ✓ Review PR"

Input: list_tasks(user_id="user_456", status="all")
Output: "You have no tasks."
```

---

### complete_task

Marks a task as complete. Implements ownership double-check.

**Signature**:
```python
@mcp.tool()
async def complete_task(
    user_id: Annotated[str, "The authenticated user's ID from JWT sub claim"],
    task_id: Annotated[int, "The ID of the task to mark as complete"]
) -> str:
    """Mark a task as complete. Verifies ownership before modification."""
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | string | Yes | User ID from JWT (for ownership verification) |
| task_id | integer | Yes | ID of the task to complete |

**Returns**: Success message or error string

**Examples**:
```
Input: complete_task(user_id="user_123", task_id=42)
Output: "Task 'Buy groceries' marked as complete."

Input: complete_task(user_id="user_123", task_id=999)
Output: "Error: Task not found or unauthorized"

Input: complete_task(user_id="user_456", task_id=42)  # Task belongs to user_123
Output: "Error: Task not found or unauthorized"
```

**Security**: Implements ownership double-check per `mcp-ownership-verification` skill.

---

## Implementation Pattern

All tools follow this pattern:

```python
# backend/src/mcp/tools/task_tools.py
from fastmcp import FastMCP
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.task import Task
from db.session import get_session

mcp = FastMCP("task-tools")

async def verify_task_ownership(
    task_id: int,
    user_id: str,
    session: AsyncSession
) -> Task | None:
    """Double-check ownership before modification."""
    statement = select(Task).where(
        Task.id == task_id,
        Task.user_id == user_id
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()

@mcp.tool()
async def add_task(
    user_id: Annotated[str, "The authenticated user's ID"],
    title: Annotated[str, "Title of the task"],
    description: Annotated[str, "Optional description"] = None
) -> str:
    """Create a new task for the user."""
    if not title or not title.strip():
        return "Error: Title is required and cannot be empty."

    async with get_session() as session:
        task = Task(
            user_id=user_id,
            title=title.strip(),
            description=description,
            is_completed=False
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)

        return f"Task '{task.title}' added with ID {task.id}."

@mcp.tool()
async def list_tasks(
    user_id: Annotated[str, "The authenticated user's ID"],
    status: Annotated[str, "Filter: 'all', 'pending', 'completed'"] = "all"
) -> str:
    """List the user's tasks with optional status filter."""
    async with get_session() as session:
        statement = select(Task).where(Task.user_id == user_id)

        if status == "pending":
            statement = statement.where(Task.is_completed == False)
        elif status == "completed":
            statement = statement.where(Task.is_completed == True)

        statement = statement.order_by(Task.created_at.desc())
        result = await session.execute(statement)
        tasks = result.scalars().all()

        if not tasks:
            return "You have no tasks."

        status_label = f"{status} " if status != "all" else ""
        lines = [f"Your {status_label}tasks:"]
        for task in tasks:
            icon = "✓" if task.is_completed else "○"
            lines.append(f"- [{task.id}] {icon} {task.title}")

        return "\n".join(lines)

@mcp.tool()
async def complete_task(
    user_id: Annotated[str, "The authenticated user's ID"],
    task_id: Annotated[int, "The ID of the task to complete"]
) -> str:
    """Mark a task as complete. Verifies ownership."""
    async with get_session() as session:
        # Double-check ownership
        task = await verify_task_ownership(task_id, user_id, session)

        if not task:
            return "Error: Task not found or unauthorized"

        task.is_completed = True
        await session.commit()

        return f"Task '{task.title}' marked as complete."
```

## Agent System Prompt

The AI agent should be configured with this system prompt:

```text
You are a helpful task management assistant. You help users manage their to-do list through natural conversation.

You have access to these tools:
- add_task: Create a new task
- list_tasks: View tasks (all, pending, or completed)
- complete_task: Mark a task as done

Guidelines:
1. When a user wants to add a task, extract the title from their message
2. When listing tasks, ask if they want all, pending, or completed if unclear
3. When completing a task, confirm which task if the request is ambiguous
4. Always confirm actions you've taken
5. If a tool returns an error, explain it to the user in friendly terms
6. Never make up task IDs - always use list_tasks first if you need to reference a specific task
```

## Error Handling

All tools return error strings (not exceptions) so the agent can communicate naturally:

| Error | Tool Response | Agent Should Say |
|-------|---------------|------------------|
| Empty title | "Error: Title is required..." | "I need a title for the task. What would you like to call it?" |
| Task not found | "Error: Task not found or unauthorized" | "I couldn't find that task. Would you like me to list your tasks?" |
| Invalid status | "Error: Invalid status..." | "I can show you all tasks, pending tasks, or completed tasks. Which would you prefer?" |

## Security Checklist

- [x] All tools require `user_id` parameter
- [x] `user_id` extracted from JWT at route level (not user input)
- [x] `complete_task` implements ownership double-check
- [x] Error messages don't leak information about other users' tasks
- [x] All database queries filter by `user_id`
