---
name: cli-to-api-migration
description: Procedures for refactoring legacy Python CLI code into RESTful FastAPI endpoints.
---

# CLI to API Migration Procedure

## Overview

This skill defines the step-by-step procedure for refactoring legacy Python CLI code into async FastAPI endpoints while preserving the original CLI functionality per constitution Principle III (Service Layer Transformation).

## Core Principle

**CRITICAL**: Original CLI code MUST be preserved and wrapped, not deleted or rewritten. The service layer acts as an adapter that exposes CLI functionality via HTTP endpoints.

## Migration Steps

### 1. Extraction

**Identify functions in the CLI app that perform data operations** (e.g., `add_task`, `list_tasks`, `update_task`, `delete_task`).

**Example - Original CLI Code**:
```python
# backend/src/cli/todo_cli.py (PRESERVE THIS FILE)
import json
from datetime import datetime

def add_task(title: str, description: str = None) -> dict:
    """Original CLI function - DO NOT MODIFY"""
    task = {
        "title": title,
        "description": description,
        "completed": False,
        "created": datetime.utcnow().isoformat()
    }
    # Original CLI logic here
    return task

def list_tasks() -> list[dict]:
    """Original CLI function - DO NOT MODIFY"""
    # Original CLI logic to read from file/database
    return []

def update_task(task_id: str, title: str = None, description: str = None) -> dict:
    """Original CLI function - DO NOT MODIFY"""
    # Original CLI logic here
    return {}

def delete_task(task_id: str) -> bool:
    """Original CLI function - DO NOT MODIFY"""
    # Original CLI logic here
    return True

def toggle_completion(task_id: str) -> dict:
    """Original CLI function - DO NOT MODIFY"""
    # Original CLI logic here
    return {}
```

### 2. Decoupling

**Remove all `input()`, `print()`, and `while True` loops from these functions.**

**Before (CLI with I/O)**:
```python
def add_task_interactive():
    """BAD: Coupled to CLI I/O"""
    title = input("Enter task title: ")
    description = input("Enter description (optional): ")

    task = add_task(title, description)

    print(f"Task created: {task['title']}")
    return task
```

**After (Pure business logic)**:
```python
def add_task(title: str, description: str = None) -> dict:
    """GOOD: Pure function, no I/O"""
    task = {
        "title": title,
        "description": description,
        "completed": False,
        "created": datetime.utcnow().isoformat()
    }
    return task
```

### 3. Service Layer

**Move these functions into a `TodoService` class that accepts Pydantic models as input.**

```python
# backend/src/services/todo_service.py
from sqlmodel import select, Session
from typing import Optional
from uuid import UUID
from datetime import datetime

from models.todo import Todo, TodoCreate, TodoUpdate
from cli.todo_cli import (
    add_task as cli_add_task,
    list_tasks as cli_list_tasks,
    update_task as cli_update_task,
    delete_task as cli_delete_task,
    toggle_completion as cli_toggle_completion
)

class TodoService:
    """
    Service layer that wraps CLI functions and adds:
    - User context (user_id)
    - Database persistence
    - Async operations
    """

    @staticmethod
    async def create_todo(
        todo_data: TodoCreate,
        user_id: str,
        session: Session
    ) -> Todo:
        """
        Wrap CLI add_task function with user context and database persistence
        """
        # Call original CLI function (preserved)
        cli_result = cli_add_task(
            title=todo_data.title,
            description=todo_data.description
        )

        # Add user context and persist to database
        todo = Todo(
            **cli_result,
            user_id=user_id,
            is_completed=cli_result.get("completed", False),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        session.add(todo)
        await session.commit()
        await session.refresh(todo)

        return todo

    @staticmethod
    async def get_user_todos(
        user_id: str,
        session: Session
    ) -> list[Todo]:
        """
        Wrap CLI list_tasks with user isolation
        """
        statement = select(Todo).where(Todo.user_id == user_id).order_by(Todo.created_at.desc())
        result = await session.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def get_user_todo(
        todo_id: UUID,
        user_id: str,
        session: Session
    ) -> Optional[Todo]:
        """
        Get single todo with user isolation
        """
        statement = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_todo(
        todo_id: UUID,
        todo_data: TodoUpdate,
        user_id: str,
        session: Session
    ) -> Optional[Todo]:
        """
        Wrap CLI update_task with user isolation
        """
        # Fetch with user isolation
        todo = await TodoService.get_user_todo(todo_id, user_id, session)

        if not todo:
            return None

        # Call original CLI function (preserved)
        cli_result = cli_update_task(
            task_id=str(todo.id),
            title=todo_data.title,
            description=todo_data.description
        )

        # Update database record
        update_data = todo_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(todo, key, value)

        todo.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(todo)

        return todo

    @staticmethod
    async def delete_todo(
        todo_id: UUID,
        user_id: str,
        session: Session
    ) -> bool:
        """
        Wrap CLI delete_task with user isolation
        """
        todo = await TodoService.get_user_todo(todo_id, user_id, session)

        if not todo:
            return False

        # Call original CLI function (preserved)
        cli_delete_task(str(todo.id))

        # Delete from database
        await session.delete(todo)
        await session.commit()

        return True

    @staticmethod
    async def toggle_completion(
        todo_id: UUID,
        user_id: str,
        session: Session
    ) -> Optional[Todo]:
        """
        Wrap CLI toggle_completion with user isolation
        """
        todo = await TodoService.get_user_todo(todo_id, user_id, session)

        if not todo:
            return None

        # Call original CLI function (preserved)
        cli_result = cli_toggle_completion(str(todo.id))

        # Update database record
        todo.is_completed = not todo.is_completed
        todo.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(todo)

        return todo
```

### 4. Async Conversion

**Wrap logic in `async def` to allow for non-blocking I/O operations.**

**Key Patterns**:

1. **All service methods are async**:
   ```python
   async def create_todo(...) -> Todo:
       # Async operations
   ```

2. **Database operations use await**:
   ```python
   await session.commit()
   await session.refresh(todo)
   result = await session.execute(statement)
   ```

3. **CLI functions remain synchronous** (they're wrapped, not modified):
   ```python
   # CLI function (synchronous - preserved)
   cli_result = cli_add_task(title, description)

   # Service layer (async - new)
   await session.commit()
   ```

### 5. FastAPI Integration

**Create FastAPI route handlers that use the service layer.**

```python
# backend/src/api/routes/todos.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from uuid import UUID

from api.middleware.auth import get_current_user_id
from db.session import get_session
from models.todo import TodoCreate, TodoUpdate, TodoResponse
from services.todo_service import TodoService

router = APIRouter(prefix="/api/todos", tags=["todos"])

@router.post("/", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_todo(
    todo_data: TodoCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new todo for the authenticated user
    """
    todo = await TodoService.create_todo(todo_data, user_id, session)
    return todo

@router.get("/", response_model=list[TodoResponse])
async def list_todos(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: AsyncSession = Depends(get_session)
):
    """
    List all todos for the authenticated user
    """
    todos = await TodoService.get_user_todos(user_id, session)
    return todos

@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific todo by ID
    """
    todo = await TodoService.get_user_todo(todo_id, user_id, session)

    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    return todo

@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: UUID,
    todo_data: TodoUpdate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: AsyncSession = Depends(get_session)
):
    """
    Update an existing todo
    """
    todo = await TodoService.update_todo(todo_id, todo_data, user_id, session)

    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    return todo

@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a todo
    """
    success = await TodoService.delete_todo(todo_id, user_id, session)

    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")

@router.patch("/{todo_id}/complete", response_model=TodoResponse)
async def toggle_completion(
    todo_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: AsyncSession = Depends(get_session)
):
    """
    Toggle todo completion status
    """
    todo = await TodoService.toggle_completion(todo_id, user_id, session)

    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    return todo
```

## Migration Checklist

- [ ] Original CLI code preserved in `backend/src/cli/` directory
- [ ] CLI functions remain synchronous and independently executable
- [ ] Service layer created in `backend/src/services/`
- [ ] Service methods are async (`async def`)
- [ ] Service layer imports and calls CLI functions
- [ ] Service layer adds user_id context
- [ ] Service layer handles database persistence
- [ ] FastAPI routes use service layer (not CLI directly)
- [ ] All database operations use `await`
- [ ] No business logic duplication between CLI and service layer
- [ ] CLI can still be used independently for testing

## Testing Strategy

### Test CLI Functions Independently
```python
# backend/tests/test_cli.py
from cli.todo_cli import add_task, list_tasks

def test_cli_add_task():
    """Test original CLI function works independently"""
    result = add_task("Test task", "Test description")
    assert result["title"] == "Test task"
    assert result["completed"] == False
```

### Test Service Layer
```python
# backend/tests/test_service.py
import pytest
from services.todo_service import TodoService

@pytest.mark.asyncio
async def test_create_todo_with_user_context(session):
    """Test service layer adds user context"""
    todo_data = TodoCreate(title="Test", description="Test")
    todo = await TodoService.create_todo(todo_data, "user_123", session)

    assert todo.user_id == "user_123"
    assert todo.title == "Test"
```

### Test API Endpoints
```python
# backend/tests/test_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_todo_endpoint(client: AsyncClient, auth_token: str):
    """Test API endpoint uses service layer"""
    response = await client.post(
        "/api/todos",
        json={"title": "Test", "description": "Test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Test"
```

## Common Pitfalls

### ❌ DON'T: Delete or modify original CLI code
```python
# BAD: Modifying original CLI function
def add_task(title: str, description: str, user_id: str) -> dict:
    # This breaks the CLI's independent functionality
```

### ✅ DO: Preserve CLI and wrap in service layer
```python
# GOOD: CLI preserved, service layer adds context
from cli.todo_cli import add_task as cli_add_task

async def create_todo(todo_data: TodoCreate, user_id: str, session: Session) -> Todo:
    cli_result = cli_add_task(todo_data.title, todo_data.description)
    # Add user context and persist
```

### ❌ DON'T: Call CLI functions directly from routes
```python
# BAD: Route calls CLI directly
@router.post("/todos")
async def create_todo(todo_data: TodoCreate):
    result = cli_add_task(todo_data.title, todo_data.description)
    # Missing user context, no database persistence
```

### ✅ DO: Use service layer in routes
```python
# GOOD: Route uses service layer
@router.post("/todos")
async def create_todo(
    todo_data: TodoCreate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    return await TodoService.create_todo(todo_data, user_id, session)
```

## Benefits of This Approach

1. **Backward Compatibility**: CLI remains functional for scripts and automation
2. **Gradual Migration**: Can migrate one function at a time
3. **Reduced Risk**: Original logic preserved, reducing regression risk
4. **Multiple Interfaces**: Same logic accessible via CLI and API
5. **Testability**: Can test CLI and service layer independently
6. **Constitution Compliance**: Satisfies Principle III (Service Layer Transformation)

## References

- Constitution Principle III: Service Layer Transformation
- FastAPI Async Documentation: https://fastapi.tiangolo.com/async/
- SQLModel Async: https://sqlmodel.tiangolo.com/tutorial/async/
