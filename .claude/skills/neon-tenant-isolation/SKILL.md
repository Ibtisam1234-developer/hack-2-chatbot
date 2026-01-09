---
name: neon-tenant-isolation
description: Strict instructions for ensuring every database query filters by user_id and handles Neon's serverless connection pooling.
---

# Neon Tenant Isolation Protocol

## Overview

This skill defines strict rules for enforcing user isolation in all database queries and configuring Neon PostgreSQL's serverless connection pooling for optimal performance and security per constitution Principle IV (Security: User Isolation).

## Core Principle

**CRITICAL**: Every database query that reads or modifies user data MUST include a WHERE clause filtering by user_id. No query may access data belonging to other users.

## User Isolation Rules

### Rule 1: Extract user_id from JWT at Entry Point

**MUST**: Extract user_id from JWT `sub` claim at the route handler level using FastAPI dependency injection.

```python
# backend/src/api/routes/todos.py
from fastapi import Depends
from typing import Annotated
from api.middleware.auth import get_current_user_id

@router.get("/api/todos")
async def list_todos(
    user_id: Annotated[str, Depends(get_current_user_id)],  # ✅ REQUIRED
    session: AsyncSession = Depends(get_session)
):
    # user_id is now available and verified
    pass
```

**Why**: Dependency injection ensures user_id is always available and impossible to forget.

### Rule 2: Pass user_id Explicitly to All Data Access Functions

**MUST**: Pass user_id as an explicit parameter to all service layer functions.

```python
# backend/src/services/todo_service.py
class TodoService:
    @staticmethod
    async def get_user_todos(
        user_id: str,  # ✅ REQUIRED: Explicit parameter
        session: AsyncSession
    ) -> list[Todo]:
        statement = select(Todo).where(Todo.user_id == user_id)
        result = await session.execute(statement)
        return result.scalars().all()
```

**Why**: Explicit parameters make user_id filtering visible in function signatures and prevent accidental omission.

### Rule 3: All SELECT Queries MUST Filter by user_id

**MUST**: Include `WHERE user_id = ?` in all SELECT queries.

```python
# ✅ CORRECT: Filters by user_id
statement = select(Todo).where(Todo.user_id == user_id)

# ❌ WRONG: No user_id filter (security violation)
statement = select(Todo)  # Returns ALL users' todos
```

**Pattern for Single Record**:
```python
async def get_user_todo(
    todo_id: UUID,
    user_id: str,
    session: AsyncSession
) -> Optional[Todo]:
    """Get single todo with user isolation"""
    statement = select(Todo).where(
        Todo.id == todo_id,
        Todo.user_id == user_id  # ✅ REQUIRED
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()
```

**Pattern for List**:
```python
async def get_user_todos(
    user_id: str,
    session: AsyncSession
) -> list[Todo]:
    """Get all todos for user"""
    statement = select(Todo).where(
        Todo.user_id == user_id  # ✅ REQUIRED
    ).order_by(Todo.created_at.desc())
    result = await session.execute(statement)
    return result.scalars().all()
```

### Rule 4: All UPDATE Queries MUST Filter by user_id

**MUST**: Include `WHERE user_id = ?` in all UPDATE queries.

```python
async def update_todo(
    todo_id: UUID,
    todo_data: TodoUpdate,
    user_id: str,
    session: AsyncSession
) -> Optional[Todo]:
    """Update todo with user isolation"""
    # Fetch with user isolation
    statement = select(Todo).where(
        Todo.id == todo_id,
        Todo.user_id == user_id  # ✅ REQUIRED
    )
    result = await session.execute(statement)
    todo = result.scalar_one_or_none()

    if not todo:
        return None  # Not found or doesn't belong to user

    # Update only if user owns the todo
    update_data = todo_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(todo, key, value)

    todo.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(todo)

    return todo
```

### Rule 5: All DELETE Queries MUST Filter by user_id

**MUST**: Include `WHERE user_id = ?` in all DELETE queries.

```python
async def delete_todo(
    todo_id: UUID,
    user_id: str,
    session: AsyncSession
) -> bool:
    """Delete todo with user isolation"""
    statement = select(Todo).where(
        Todo.id == todo_id,
        Todo.user_id == user_id  # ✅ REQUIRED
    )
    result = await session.execute(statement)
    todo = result.scalar_one_or_none()

    if not todo:
        return False  # Not found or doesn't belong to user

    await session.delete(todo)
    await session.commit()

    return True
```

### Rule 6: No Global Queries Without Explicit Admin Authorization

**MUST**: Never execute queries without user_id filter unless explicitly authorized as admin operation.

```python
# ❌ WRONG: Global query without authorization
async def get_all_todos(session: AsyncSession) -> list[Todo]:
    """SECURITY VIOLATION: Returns all users' todos"""
    statement = select(Todo)
    result = await session.execute(statement)
    return result.scalars().all()

# ✅ CORRECT: Admin query with explicit authorization check
async def admin_get_all_todos(
    admin_user_id: str,
    session: AsyncSession
) -> list[Todo]:
    """Admin-only operation with explicit authorization"""
    # Check if user is admin
    if not await is_admin(admin_user_id, session):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Only then allow global query
    statement = select(Todo)
    result = await session.execute(statement)
    return result.scalars().all()
```

### Rule 7: Audit Logs MUST Capture user_id

**MUST**: All data modifications must log the user_id for audit trail.

```python
async def create_todo(
    todo_data: TodoCreate,
    user_id: str,
    session: AsyncSession
) -> Todo:
    """Create todo with audit logging"""
    todo = Todo(
        **todo_data.model_dump(),
        user_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(todo)
    await session.commit()

    # Audit log
    logger.info(f"Todo created: id={todo.id}, user_id={user_id}, title={todo.title}")

    await session.refresh(todo)
    return todo
```

## Neon Serverless Connection Pooling

### Configuration

**MUST**: Configure asyncpg engine with Neon-optimized settings.

```python
# backend/src/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
import os

# Connection string format for Neon
DATABASE_URL = os.getenv("DATABASE_URL")
# Example: postgresql+asyncpg://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb

# Engine configuration optimized for Neon serverless
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set True for SQL logging in development
    pool_pre_ping=True,  # ✅ CRITICAL: Verify connections before use (handles serverless cold starts)
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Additional connections when pool exhausted
    pool_recycle=3600,  # ✅ CRITICAL: Recycle connections after 1 hour (prevents stale connections)
    connect_args={
        "server_settings": {
            "application_name": "todoweb_api"  # Helps identify connections in Neon dashboard
        }
    }
)

# Session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # Prevent lazy loading issues
)
```

### Key Settings Explained

1. **pool_pre_ping=True**
   - **Purpose**: Verifies connection is alive before using it
   - **Why**: Neon serverless may close idle connections; pre-ping detects and recreates them
   - **Impact**: Prevents "connection closed" errors

2. **pool_recycle=3600**
   - **Purpose**: Recycles connections after 1 hour
   - **Why**: Prevents stale connections in serverless environment
   - **Impact**: Ensures fresh connections, reduces connection errors

3. **pool_size=10, max_overflow=20**
   - **Purpose**: Manages connection pool size
   - **Why**: Balances performance and resource usage
   - **Impact**: Supports up to 30 concurrent connections

### Session Management

**MUST**: Always use async context managers for database sessions.

```python
# backend/src/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import async_session

async def get_session() -> AsyncSession:
    """
    FastAPI dependency for database sessions
    Ensures proper session lifecycle management
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

**Usage in Routes**:
```python
@router.get("/api/todos")
async def list_todos(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: AsyncSession = Depends(get_session)  # ✅ Automatic session management
):
    todos = await TodoService.get_user_todos(user_id, session)
    return todos
```

### Error Handling for Connection Issues

**MUST**: Handle asyncpg connection errors gracefully.

```python
from asyncpg.exceptions import PostgresError
from fastapi import HTTPException

async def get_user_todos(
    user_id: str,
    session: AsyncSession
) -> list[Todo]:
    """Get todos with connection error handling"""
    try:
        statement = select(Todo).where(Todo.user_id == user_id)
        result = await session.execute(statement)
        return result.scalars().all()
    except PostgresError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable"
        )
```

## Database Schema Requirements

### Table Schema with user_id

**MUST**: Include user_id column with index in all user-owned tables.

```sql
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,  -- ✅ REQUIRED: Foreign key to user
    title VARCHAR(200) NOT NULL,
    description TEXT,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ✅ CRITICAL: Index on user_id for query performance
CREATE INDEX idx_todos_user_id ON todos(user_id);

-- ✅ RECOMMENDED: Composite index for common query patterns
CREATE INDEX idx_todos_user_completed ON todos(user_id, is_completed);
```

### SQLModel Schema

**MUST**: Include user_id field with index in SQLModel definitions.

```python
# backend/src/models/todo.py
from sqlmodel import SQLModel, Field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

class Todo(SQLModel, table=True):
    """Database model with user isolation"""
    __tablename__ = "todos"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(index=True, nullable=False)  # ✅ REQUIRED: Indexed for performance
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    is_completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

## Security Testing

### Test User Isolation

**MUST**: Write tests that verify User A cannot access User B's data.

```python
# backend/tests/test_user_isolation.py
import pytest
from httpx import AsyncClient
from uuid import uuid4

@pytest.mark.asyncio
async def test_user_cannot_access_other_user_todos(client: AsyncClient):
    """Test that User A cannot access User B's todos"""
    # Create todo for User A
    user_a_token = create_test_token("user_a")
    response = await client.post(
        "/api/todos",
        json={"title": "User A's todo"},
        headers={"Authorization": f"Bearer {user_a_token}"}
    )
    assert response.status_code == 201
    todo_id = response.json()["id"]

    # Attempt to access with User B's token
    user_b_token = create_test_token("user_b")
    response = await client.get(
        f"/api/todos/{todo_id}",
        headers={"Authorization": f"Bearer {user_b_token}"}
    )

    # ✅ MUST return 404 (not 403, to prevent information leakage)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_user_cannot_update_other_user_todos(client: AsyncClient):
    """Test that User A cannot update User B's todos"""
    # Create todo for User A
    user_a_token = create_test_token("user_a")
    response = await client.post(
        "/api/todos",
        json={"title": "User A's todo"},
        headers={"Authorization": f"Bearer {user_a_token}"}
    )
    todo_id = response.json()["id"]

    # Attempt to update with User B's token
    user_b_token = create_test_token("user_b")
    response = await client.put(
        f"/api/todos/{todo_id}",
        json={"title": "Hacked!"},
        headers={"Authorization": f"Bearer {user_b_token}"}
    )

    # ✅ MUST return 404
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_user_cannot_delete_other_user_todos(client: AsyncClient):
    """Test that User A cannot delete User B's todos"""
    # Create todo for User A
    user_a_token = create_test_token("user_a")
    response = await client.post(
        "/api/todos",
        json={"title": "User A's todo"},
        headers={"Authorization": f"Bearer {user_a_token}"}
    )
    todo_id = response.json()["id"]

    # Attempt to delete with User B's token
    user_b_token = create_test_token("user_b")
    response = await client.delete(
        f"/api/todos/{todo_id}",
        headers={"Authorization": f"Bearer {user_b_token}"}
    )

    # ✅ MUST return 404
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_list_todos_returns_only_user_todos(client: AsyncClient):
    """Test that list endpoint returns only authenticated user's todos"""
    # Create todos for User A
    user_a_token = create_test_token("user_a")
    await client.post(
        "/api/todos",
        json={"title": "User A todo 1"},
        headers={"Authorization": f"Bearer {user_a_token}"}
    )
    await client.post(
        "/api/todos",
        json={"title": "User A todo 2"},
        headers={"Authorization": f"Bearer {user_a_token}"}
    )

    # Create todos for User B
    user_b_token = create_test_token("user_b")
    await client.post(
        "/api/todos",
        json={"title": "User B todo 1"},
        headers={"Authorization": f"Bearer {user_b_token}"}
    )

    # List todos for User A
    response = await client.get(
        "/api/todos",
        headers={"Authorization": f"Bearer {user_a_token}"}
    )

    # ✅ MUST return only User A's todos (2 items)
    assert response.status_code == 200
    todos = response.json()
    assert len(todos) == 2
    assert all(todo["title"].startswith("User A") for todo in todos)
```

## Security Checklist

- [ ] All SELECT queries filter by user_id
- [ ] All UPDATE queries filter by user_id
- [ ] All DELETE queries filter by user_id
- [ ] user_id extracted from JWT sub claim at route level
- [ ] user_id passed explicitly to all service functions
- [ ] No global queries without admin authorization
- [ ] Database schema includes user_id column with index
- [ ] SQLModel includes user_id field with index=True
- [ ] Neon engine configured with pool_pre_ping=True
- [ ] Neon engine configured with pool_recycle=3600
- [ ] Session management uses async context managers
- [ ] User isolation tests written and passing
- [ ] Audit logs capture user_id for all modifications
- [ ] 404 returned for unauthorized access (not 403)

## Common Pitfalls

### ❌ Pitfall 1: Forgetting user_id Filter

```python
# BAD: No user_id filter
async def get_todo(todo_id: UUID, session: AsyncSession) -> Optional[Todo]:
    statement = select(Todo).where(Todo.id == todo_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()
```

**Fix**: Always include user_id filter
```python
# GOOD: Includes user_id filter
async def get_user_todo(
    todo_id: UUID,
    user_id: str,
    session: AsyncSession
) -> Optional[Todo]:
    statement = select(Todo).where(
        Todo.id == todo_id,
        Todo.user_id == user_id
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()
```

### ❌ Pitfall 2: Using 403 Instead of 404

```python
# BAD: Returns 403 (reveals todo exists)
if todo.user_id != user_id:
    raise HTTPException(status_code=403, detail="Access denied")
```

**Fix**: Return 404 to prevent information leakage
```python
# GOOD: Returns 404 (doesn't reveal existence)
todo = await get_user_todo(todo_id, user_id, session)
if not todo:
    raise HTTPException(status_code=404, detail="Todo not found")
```

### ❌ Pitfall 3: Not Using pool_pre_ping

```python
# BAD: No pool_pre_ping (connection errors in serverless)
engine = create_async_engine(DATABASE_URL)
```

**Fix**: Enable pool_pre_ping for Neon
```python
# GOOD: pool_pre_ping handles serverless connections
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

## Performance Considerations

1. **Index on user_id**: Critical for query performance
2. **Composite Indexes**: Optimize common query patterns (user_id + is_completed)
3. **Connection Pooling**: Reuse connections for better performance
4. **Async Operations**: Non-blocking I/O for concurrent requests
5. **Query Optimization**: Select only needed columns when possible

## References

- Constitution Principle IV: Security: User Isolation
- Neon Documentation: https://neon.tech/docs
- asyncpg Documentation: https://magicstack.github.io/asyncpg/
- SQLModel Async: https://sqlmodel.tiangolo.com/tutorial/async/
