# Data Model: Todo API

**Feature**: Todo API with Authentication
**Date**: 2026-01-07
**Status**: Complete

## Overview

This document defines the data model for the Todo API, including database schema, SQLModel definitions, validation rules, and relationships. All models enforce user isolation per constitution Principle IV.

## Entity: Todo

### Description

Represents a single todo item owned by a user. Each todo is isolated to its owner via the `user_id` foreign key extracted from JWT tokens.

### SQLModel Schema

```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

class TodoBase(SQLModel):
    """Base model with shared fields for requests/responses"""
    title: str = Field(min_length=1, max_length=200, description="Todo title (required)")
    description: Optional[str] = Field(default=None, max_length=2000, description="Optional detailed description")
    is_completed: bool = Field(default=False, description="Completion status")

class Todo(TodoBase, table=True):
    """Database model with all fields including system-generated"""
    __tablename__ = "todos"

    id: UUID = Field(default_factory=uuid4, primary_key=True, description="Unique identifier")
    user_id: str = Field(index=True, nullable=False, description="Owner user ID from JWT sub claim")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, description="Last modification timestamp")

class TodoCreate(TodoBase):
    """Request model for creating a todo (no id, user_id, or timestamps)"""
    pass

class TodoUpdate(SQLModel):
    """Request model for updating a todo (all fields optional)"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    is_completed: Optional[bool] = Field(default=None)

class TodoResponse(TodoBase):
    """Response model with all fields"""
    id: UUID
    user_id: str
    created_at: datetime
    updated_at: datetime
```

### Database Table Schema

```sql
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for user isolation queries (critical for performance)
CREATE INDEX idx_todos_user_id ON todos(user_id);

-- Composite index for common query patterns
CREATE INDEX idx_todos_user_completed ON todos(user_id, is_completed);
```

### Field Specifications

| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| id | UUID | PRIMARY KEY, NOT NULL | gen_random_uuid() | Unique identifier, system-generated |
| user_id | VARCHAR(255) | NOT NULL, INDEXED | - | Owner's user ID from JWT sub claim |
| title | VARCHAR(200) | NOT NULL, 1-200 chars | - | Todo title, required |
| description | TEXT | NULLABLE, max 2000 chars | NULL | Optional detailed description |
| is_completed | BOOLEAN | NOT NULL | FALSE | Completion status |
| created_at | TIMESTAMP | NOT NULL | NOW() | Creation timestamp (UTC) |
| updated_at | TIMESTAMP | NOT NULL | NOW() | Last modification timestamp (UTC) |

### Validation Rules

1. **Title**:
   - Required (cannot be empty or null)
   - Minimum length: 1 character
   - Maximum length: 200 characters
   - Trimmed of leading/trailing whitespace

2. **Description**:
   - Optional (can be null)
   - Maximum length: 2000 characters
   - Trimmed of leading/trailing whitespace

3. **User ID**:
   - Required (cannot be null)
   - Extracted from JWT sub claim
   - Never provided by client (security)
   - Automatically set by backend

4. **Completion Status**:
   - Boolean (true/false)
   - Defaults to false (incomplete)
   - Can be toggled via PATCH endpoint

5. **Timestamps**:
   - Automatically set by database
   - UTC timezone
   - `updated_at` refreshed on every UPDATE

### Relationships

```
User (managed by Better Auth)
  ↓ 1:N
Todo (this entity)
```

- **One-to-Many**: One user has many todos
- **Foreign Key**: `user_id` references user in Better Auth system
- **Cascade**: Not applicable (Better Auth manages users separately)
- **Orphan Handling**: Todos remain if user deleted (business decision needed)

### Indexes

1. **Primary Index**: `id` (UUID) - Fast lookups by todo ID
2. **User Isolation Index**: `user_id` - Critical for filtering queries
3. **Composite Index**: `(user_id, is_completed)` - Optimizes filtered lists

**Index Rationale**:
- Every query filters by `user_id` (constitution requirement)
- Common pattern: "show me my incomplete todos"
- Index on `user_id` alone covers most queries
- Composite index optimizes completion-filtered queries

### State Transitions

```
[Created] → is_completed = false
    ↓
[Toggle Complete] → is_completed = true
    ↓
[Toggle Incomplete] → is_completed = false
    ↓
[Deleted] → (removed from database)
```

**Valid Transitions**:
- Create → Incomplete (default)
- Incomplete ↔ Complete (toggle)
- Any State → Deleted

**Invalid Transitions**: None (all states are valid)

## Entity: User (External)

### Description

Users are managed by Better Auth and not stored in our database. We only reference the `user_id` from JWT tokens.

### JWT Payload Structure

```json
{
  "sub": "user_123abc",           // user_id (our foreign key)
  "email": "user@example.com",    // optional, not used
  "iat": 1704672000,              // issued at
  "exp": 1705276800               // expires at
}
```

### Integration Points

- **JWT sub claim**: Contains the user_id we use as foreign key
- **No local user table**: Better Auth is source of truth
- **No user validation**: Trust JWT signature verification
- **No user queries**: Only filter todos by user_id

## CLI Data Structure Mapping

### Legacy CLI Format (Assumed)

```python
# Existing CLI todo structure (to be preserved)
{
    "title": "Buy groceries",
    "description": "Milk, eggs, bread",
    "completed": false,
    "created": "2026-01-07T10:00:00Z"
}
```

### Migration Mapping

| CLI Field | Database Field | Transformation |
|-----------|----------------|----------------|
| title | title | Direct mapping (no change) |
| description | description | Direct mapping (no change) |
| completed | is_completed | Rename field |
| created | created_at | Rename field, ensure UTC |
| (none) | id | Generate UUID |
| (none) | user_id | Add from JWT context |
| (none) | updated_at | Set to created_at initially |

### Migration Script Pseudocode

```python
async def migrate_cli_todo_to_db(cli_todo: dict, user_id: str) -> Todo:
    """
    Migrate a CLI todo to database format
    Preserves original data, adds required fields
    """
    return Todo(
        id=uuid4(),  # Generate new UUID
        user_id=user_id,  # From JWT context
        title=cli_todo["title"],
        description=cli_todo.get("description"),
        is_completed=cli_todo.get("completed", False),
        created_at=parse_datetime(cli_todo.get("created", datetime.utcnow())),
        updated_at=parse_datetime(cli_todo.get("created", datetime.utcnow()))
    )
```

## Database Connection Configuration

### Neon PostgreSQL with asyncpg

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# Connection string format
DATABASE_URL = "postgresql+asyncpg://user:password@host.neon.tech:5432/database"

# Engine configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set True for SQL logging in development
    pool_pre_ping=True,  # Verify connections before use (important for serverless)
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Additional connections when pool exhausted
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create tables
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

### Connection Best Practices

1. **Pool Pre-Ping**: Verify connections before use (handles serverless cold starts)
2. **Pool Recycling**: Recycle connections periodically (prevents stale connections)
3. **Async Context**: Always use `async with` for sessions
4. **Error Handling**: Catch `asyncpg` exceptions and return appropriate HTTP errors

## Query Patterns

### List All Todos for User

```python
from sqlmodel import select

async def get_user_todos(user_id: str, session: AsyncSession) -> list[Todo]:
    statement = select(Todo).where(Todo.user_id == user_id).order_by(Todo.created_at.desc())
    result = await session.execute(statement)
    return result.scalars().all()
```

### Get Single Todo (with User Isolation)

```python
async def get_user_todo(todo_id: UUID, user_id: str, session: AsyncSession) -> Todo | None:
    statement = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()
```

### Create Todo

```python
async def create_todo(todo_data: TodoCreate, user_id: str, session: AsyncSession) -> Todo:
    todo = Todo(
        **todo_data.model_dump(),
        user_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(todo)
    await session.commit()
    await session.refresh(todo)
    return todo
```

### Update Todo

```python
async def update_todo(todo_id: UUID, todo_data: TodoUpdate, user_id: str, session: AsyncSession) -> Todo | None:
    # Fetch with user isolation
    statement = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
    result = await session.execute(statement)
    todo = result.scalar_one_or_none()

    if not todo:
        return None

    # Update only provided fields
    update_data = todo_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(todo, key, value)

    todo.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(todo)
    return todo
```

### Delete Todo

```python
async def delete_todo(todo_id: UUID, user_id: str, session: AsyncSession) -> bool:
    statement = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
    result = await session.execute(statement)
    todo = result.scalar_one_or_none()

    if not todo:
        return False

    await session.delete(todo)
    await session.commit()
    return True
```

### Toggle Completion

```python
async def toggle_completion(todo_id: UUID, user_id: str, session: AsyncSession) -> Todo | None:
    statement = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
    result = await session.execute(statement)
    todo = result.scalar_one_or_none()

    if not todo:
        return None

    todo.is_completed = not todo.is_completed
    todo.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(todo)
    return todo
```

## Security Considerations

1. **User Isolation**: Every query MUST include `WHERE user_id = ?`
2. **No User Input for user_id**: Always extract from JWT, never from request body
3. **UUID Primary Keys**: Prevents enumeration attacks
4. **Input Validation**: SQLModel validates all fields automatically
5. **SQL Injection**: Parameterized queries prevent injection

## Performance Considerations

1. **Indexes**: `user_id` index critical for query performance
2. **Connection Pooling**: Reuse connections for better performance
3. **Async Operations**: Non-blocking I/O for concurrent requests
4. **Query Optimization**: Select only needed columns when possible
5. **Pagination**: Consider adding pagination for large todo lists (future)

## Testing Strategy

1. **Unit Tests**: Test each query function with mock data
2. **Integration Tests**: Test with real Neon DB (test database)
3. **Security Tests**: Verify user isolation (attempt cross-user access)
4. **Performance Tests**: Measure query times with 100+ todos per user
5. **Migration Tests**: Verify CLI data migrates correctly

## Next Steps

1. ✅ Data model defined
2. ⏭️ Create API contracts in contracts/ directory
3. ⏭️ Create quickstart.md with setup instructions
4. ⏭️ Implement SQLModel schemas in backend/src/models/todo.py
