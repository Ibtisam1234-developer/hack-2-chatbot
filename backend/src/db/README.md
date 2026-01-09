# Database Module - Todo API

## Overview

This module provides Neon Serverless PostgreSQL integration for the Todo API with multi-tenant isolation and Better Auth compatibility.

## Architecture

- **ORM**: SQLModel (Pydantic + SQLAlchemy)
- **Driver**: asyncpg (async PostgreSQL driver)
- **Database**: Neon Serverless PostgreSQL
- **Pattern**: Async/await throughout
- **Isolation**: Multi-tenant with user_id filtering

## Key Features

### 1. Serverless Optimization
- `pool_pre_ping=True`: Validates connections before use (handles cold starts)
- Small connection pool (5 connections): Optimized for serverless
- Connection recycling: Prevents stale connections
- Exponential backoff: Retry logic for connection failures

### 2. Multi-Tenant Isolation
- Every table includes `user_id: str` column (REQUIRED)
- `user_id` is indexed for query performance
- All queries MUST filter by `user_id`
- User ID extracted from JWT sub claim (never from client input)

### 3. Better Auth Compatibility
- No conflicts with Better Auth tables (user, session, account, verification)
- `user_id` references Better Auth's user table (managed externally)
- No foreign key constraints (Better Auth is source of truth)

## Files

```
backend/src/db/
├── __init__.py       # Package exports and initialization
├── connection.py     # Database connection and session management
├── models.py         # SQLModel schemas (Todo, TodoCreate, TodoUpdate, TodoResponse)
├── verify.py         # Verification script
└── README.md         # This file
```

## Setup

### 1. Environment Variables

Add to your `.env` file:

```bash
DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb
```

**Note**: The connection string will be automatically converted to `postgresql+asyncpg://` for async operations.

### 2. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

Required packages:
- `sqlmodel==0.0.14`
- `asyncpg==0.29.0`
- `sqlalchemy[asyncio]==2.0.25`

### 3. Initialize Database

```python
from backend.src.db import init_database

# Call during application startup
await init_database()
```

### 4. Verify Setup

```bash
python -m backend.src.db.verify
```

This will:
- Test database connectivity
- Create tables and indexes
- Verify schema matches SQLModel definitions
- Display detailed status of each check

## Usage

### In FastAPI Routes

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.db import get_session, Todo, TodoCreate

@app.post("/api/todos")
async def create_todo(
    todo_data: TodoCreate,
    user_id: str,  # Extracted from JWT middleware
    session: AsyncSession = Depends(get_session)
):
    # Create todo with user isolation
    todo = Todo(
        **todo_data.model_dump(),
        user_id=user_id  # REQUIRED for multi-tenant isolation
    )
    session.add(todo)
    await session.commit()
    await session.refresh(todo)
    return todo
```

### Query with User Isolation

```python
from sqlmodel import select
from backend.src.db import Todo

async def get_user_todos(user_id: str, session: AsyncSession):
    # ALWAYS filter by user_id
    statement = select(Todo).where(Todo.user_id == user_id)
    result = await session.execute(statement)
    return result.scalars().all()
```

### Application Lifecycle

```python
from fastapi import FastAPI
from backend.src.db import init_database, cleanup_database

app = FastAPI()

@app.on_event("startup")
async def startup():
    await init_database()

@app.on_event("shutdown")
async def shutdown():
    await cleanup_database()
```

## Database Schema

### Todos Table

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

-- Indexes
CREATE INDEX ix_todos_user_id ON todos(user_id);
CREATE INDEX idx_todos_user_completed ON todos(user_id, is_completed);
```

### Field Specifications

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier (auto-generated) |
| user_id | VARCHAR(255) | NOT NULL, INDEXED | Owner's user ID from JWT |
| title | VARCHAR(200) | NOT NULL, 1-200 chars | Todo title |
| description | TEXT | NULLABLE, max 2000 chars | Optional description |
| is_completed | BOOLEAN | NOT NULL, default FALSE | Completion status |
| created_at | TIMESTAMP | NOT NULL | Creation timestamp (UTC) |
| updated_at | TIMESTAMP | NOT NULL | Last modification timestamp (UTC) |

## SQLModel Models

### Todo (Database Model)
Full model with all fields including system-generated ones.

### TodoCreate (Request Model)
For creating todos. Excludes id, user_id, and timestamps.

### TodoUpdate (Request Model)
For updating todos. All fields optional (partial updates).

### TodoResponse (Response Model)
For API responses. Includes all fields.

## Security Considerations

### Multi-Tenant Isolation (CRITICAL)

1. **Every query MUST filter by user_id**
   ```python
   # ✓ CORRECT
   select(Todo).where(Todo.user_id == user_id)

   # ✗ WRONG - Security vulnerability!
   select(Todo)  # Returns all users' todos
   ```

2. **Never accept user_id from client input**
   ```python
   # ✓ CORRECT
   user_id = extract_from_jwt(token)

   # ✗ WRONG - Security vulnerability!
   user_id = request.body.get("user_id")
   ```

3. **Use UUID primary keys**
   - Prevents enumeration attacks
   - UUIDs are globally unique and unpredictable

### Input Validation

SQLModel automatically validates:
- Field types (string, boolean, datetime)
- String lengths (min/max)
- Required vs optional fields
- Data format (UUID, datetime)

## Performance Optimization

### Connection Pooling
- Pool size: 5 (optimized for serverless)
- Max overflow: 10 (additional connections when needed)
- Pool recycling: 3600 seconds (1 hour)

### Indexes
- `user_id`: Critical for all queries (every query filters by user_id)
- `(user_id, is_completed)`: Optimizes "show my incomplete todos" queries

### Query Patterns
- Use async/await for non-blocking I/O
- Select only needed columns when possible
- Consider pagination for large result sets

## Error Handling

### Connection Errors
```python
try:
    session = await get_session()
except ConnectionError as e:
    # Handle connection failure
    # Check DATABASE_URL is set
    # Verify Neon database is accessible
```

### Query Errors
```python
try:
    await session.execute(statement)
    await session.commit()
except Exception as e:
    await session.rollback()
    # Handle query error
```

## Testing

### Unit Tests
Test query functions with mock data:
```python
import pytest
from backend.src.db import Todo, TodoCreate

@pytest.mark.asyncio
async def test_create_todo(session):
    todo_data = TodoCreate(title="Test", description="Test todo")
    todo = Todo(**todo_data.model_dump(), user_id="test_user")
    session.add(todo)
    await session.commit()
    assert todo.id is not None
```

### Integration Tests
Test with real Neon database (test database):
```python
@pytest.mark.asyncio
async def test_user_isolation(session):
    # Create todos for two different users
    todo1 = Todo(title="User 1 Todo", user_id="user1")
    todo2 = Todo(title="User 2 Todo", user_id="user2")

    # Verify user1 cannot see user2's todos
    result = await session.execute(
        select(Todo).where(Todo.user_id == "user1")
    )
    todos = result.scalars().all()
    assert len(todos) == 1
    assert todos[0].user_id == "user1"
```

## Troubleshooting

### "DATABASE_URL environment variable not set"
- Ensure `.env` file exists in project root
- Verify `DATABASE_URL` is set with your Neon connection string
- Format: `postgresql://user:password@host.neon.tech/database`

### "Failed to connect to database"
- Check Neon database is running
- Verify connection string is correct
- Check network connectivity
- Review Neon dashboard for database status

### "Table does not exist"
- Run `await init_database()` during startup
- Or run verification script: `python -m backend.src.db.verify`

### "Connection pool exhausted"
- Increase `pool_size` in `connection.py` (default: 5)
- Check for connection leaks (ensure sessions are closed)
- Review query performance (slow queries hold connections)

## Next Steps

1. ✓ Database module created
2. ⏭️ Create JWT middleware for user_id extraction
3. ⏭️ Implement FastAPI routes with user isolation
4. ⏭️ Add integration tests for multi-tenant scenarios
5. ⏭️ Configure Better Auth for user management

## References

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Neon PostgreSQL Documentation](https://neon.tech/docs)
- [FastAPI Database Guide](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [Better Auth Documentation](https://www.better-auth.com/)
