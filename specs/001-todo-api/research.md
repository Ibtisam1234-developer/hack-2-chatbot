# Research: Todo API Technology Decisions

**Feature**: Todo API with Authentication
**Date**: 2026-01-07
**Status**: Complete

## Overview

This document captures research findings and technology decisions for implementing the Todo API with JWT authentication, async Python backend, and Next.js frontend per constitution requirements.

## Research Areas

### 1. JWT Verification Library for FastAPI

**Question**: Which JWT library should we use for token verification in FastAPI?

**Options Considered**:

| Library | Pros | Cons | Verdict |
|---------|------|------|---------|
| python-jose | Industry standard, well-maintained, supports multiple algorithms | Additional dependency | ✅ **Selected** |
| PyJWT | Lightweight, popular | Less FastAPI-specific examples | Alternative |
| authlib | Comprehensive OAuth/JWT support | Heavier than needed | Overkill |

**Decision**: **python-jose[cryptography]**

**Rationale**:
- Most commonly used with FastAPI in production
- Excellent documentation and community support
- Supports HS256 algorithm (used by Better Auth)
- Type hints compatible with FastAPI
- Handles token expiration and validation automatically

**Implementation Pattern**:
```python
from jose import jwt, JWTError

def verify_token(token: str, secret: str) -> dict:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 2. Async Database Driver for Neon PostgreSQL

**Question**: Which async driver should we use for Neon DB with SQLModel?

**Options Considered**:

| Driver | Pros | Cons | Verdict |
|--------|------|------|---------|
| asyncpg | Fastest PostgreSQL driver, async-native, Neon-optimized | PostgreSQL-only | ✅ **Selected** |
| psycopg3 (async) | Familiar API, supports both sync/async | Slower than asyncpg | Alternative |
| databases | Abstraction layer, multi-DB support | Extra abstraction overhead | Unnecessary |

**Decision**: **asyncpg**

**Rationale**:
- Neon officially recommends asyncpg for serverless PostgreSQL
- Native async implementation (not sync wrapper)
- Highest performance for concurrent connections
- Connection pooling optimized for serverless environments
- SQLModel/SQLAlchemy async support via asyncpg

**Implementation Pattern**:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host/db",
    pool_pre_ping=True,  # Verify connections before use
    pool_size=10,
    max_overflow=20
)
```

### 3. ORM/Schema Library

**Question**: Should we use SQLModel, SQLAlchemy Core, or raw SQL?

**Options Considered**:

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| SQLModel | Pydantic integration, type-safe, FastAPI-native | Newer library | ✅ **Selected** |
| SQLAlchemy Core | Mature, flexible, async support | More boilerplate, less type-safe | Alternative |
| Raw SQL | Maximum control, no ORM overhead | No type safety, manual validation | Too low-level |

**Decision**: **SQLModel**

**Rationale**:
- Built on Pydantic (same validation as FastAPI request/response models)
- Single model definition for DB schema and API schema
- Type hints enable IDE autocomplete and type checking
- Async support via SQLAlchemy 2.0
- Reduces code duplication between DB and API layers

**Implementation Pattern**:
```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from uuid import UUID, uuid4

class Todo(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(index=True)  # From JWT sub claim
    title: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 4. Better Auth JWT Plugin Configuration

**Question**: How should Better Auth be configured to generate JWT tokens compatible with FastAPI?

**Research Findings**:

Better Auth supports JWT tokens via the `jwt()` plugin:

```typescript
import { betterAuth } from "better-auth"
import { jwt } from "better-auth/plugins"

export const auth = betterAuth({
  secret: process.env.BETTER_AUTH_SECRET,
  plugins: [
    jwt({
      // JWT tokens will include user.id in the 'sub' claim
      expiresIn: "7d",
      algorithm: "HS256"
    })
  ]
})
```

**Key Points**:
- Better Auth automatically includes `user.id` in JWT `sub` claim
- Uses HS256 algorithm (symmetric signing with shared secret)
- Token format: `Authorization: Bearer <token>`
- FastAPI must use same secret to verify tokens

**Decision**: Use Better Auth jwt() plugin with HS256 algorithm

**Rationale**:
- HS256 is simpler than asymmetric algorithms (no public/private key management)
- Shared secret approach aligns with constitution requirement
- Better Auth handles token generation, FastAPI handles verification
- Standard Bearer token format works with FastAPI security utilities

### 5. API Client Pattern for Frontend

**Question**: How should the Next.js frontend attach JWT tokens to API requests?

**Options Considered**:

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Custom fetch wrapper | Simple, full control, no dependencies | Manual implementation | ✅ **Selected** |
| Axios with interceptors | Popular, built-in interceptors | Extra dependency, overkill | Unnecessary |
| SWR/React Query | Caching + auth | Complex setup for simple use case | Overkill |

**Decision**: Custom fetch wrapper with Better Auth session

**Rationale**:
- Next.js has native fetch support
- Better Auth provides `useSession()` hook for token access
- Simple wrapper function adds Authorization header
- No additional dependencies needed
- Easy to add error handling and retry logic

**Implementation Pattern**:
```typescript
import { useSession } from "@/lib/auth-client"

async function apiClient(endpoint: string, options: RequestInit = {}) {
  const session = await getSession()

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      "Authorization": `Bearer ${session.token}`,
      "Content-Type": "application/json"
    }
  })

  if (!response.ok) {
    if (response.status === 401) {
      // Token expired, redirect to login
      window.location.href = "/login"
    }
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}
```

### 6. CLI Preservation Strategy

**Question**: How should existing CLI code be preserved and wrapped?

**Research Findings**:

Constitution Principle III requires:
- Original CLI code remains intact
- Service layer imports and invokes CLI functions
- No business logic duplication

**Decision**: Adapter pattern with CLI module imports

**Architecture**:
```
backend/src/cli/todo_cli.py (existing)
  ↓ imported by
backend/src/services/todo_service.py (new adapter)
  ↓ called by
backend/src/api/routes/todos.py (FastAPI routes)
```

**Implementation Pattern**:
```python
# backend/src/cli/todo_cli.py (existing - preserved)
def create_todo(title: str, description: str = None) -> dict:
    # Original CLI logic
    return {"id": "...", "title": title, ...}

# backend/src/services/todo_service.py (new adapter)
from cli.todo_cli import create_todo as cli_create_todo

async def create_todo_for_user(user_id: str, title: str, description: str = None):
    # Wrap CLI function with user_id context
    todo_data = cli_create_todo(title, description)
    todo_data["user_id"] = user_id
    # Save to database with user_id
    return await save_todo(todo_data)
```

**Rationale**:
- CLI functions remain independently testable
- Service layer adds user_id context and database persistence
- FastAPI routes handle HTTP concerns only
- Clear separation of concerns

### 7. User Isolation Query Pattern

**Question**: How should user_id filtering be enforced in all queries?

**Decision**: Dependency injection pattern with user_id from JWT

**Implementation Pattern**:
```python
from fastapi import Depends, HTTPException
from sqlmodel import select

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    payload = verify_token(token, settings.BETTER_AUTH_SECRET)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

@app.get("/api/todos")
async def list_todos(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    # user_id automatically injected from JWT
    statement = select(Todo).where(Todo.user_id == user_id)
    result = await session.execute(statement)
    return result.scalars().all()
```

**Rationale**:
- FastAPI dependency injection ensures user_id is always available
- Impossible to forget user_id filtering (compile-time safety)
- Centralized JWT verification logic
- Consistent pattern across all endpoints

## Technology Stack Summary

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Backend Framework | FastAPI | Latest | Async-native, type-safe, OpenAPI generation |
| Backend Language | Python | 3.11+ | Async/await support, type hints |
| Database | Neon PostgreSQL | Latest | Serverless, PostgreSQL-compatible |
| DB Driver | asyncpg | Latest | Fastest async PostgreSQL driver |
| ORM | SQLModel | Latest | Pydantic integration, type-safe |
| JWT Library | python-jose | Latest | Industry standard for FastAPI |
| Frontend Framework | Next.js | 16+ | App Router, React 19 support |
| Frontend Language | TypeScript | 5+ | Type safety, IDE support |
| Auth Library | Better Auth | Latest | JWT plugin, Next.js integration |
| Testing (Backend) | pytest | Latest | Async test support |
| Testing (Frontend) | Jest + RTL | Latest | React component testing |

## Environment Variables Required

```bash
# Shared between Next.js and FastAPI
BETTER_AUTH_SECRET=<random-256-bit-secret>

# Backend (FastAPI)
DATABASE_URL=postgresql+asyncpg://user:pass@host.neon.tech/db
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend (Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
```

## Security Considerations

1. **Secret Management**: BETTER_AUTH_SECRET must be identical in both .env files
2. **Token Expiration**: Better Auth default 7 days, configurable
3. **CORS**: FastAPI must allow Next.js origin for development
4. **HTTPS**: Production deployment requires HTTPS for token security
5. **SQL Injection**: SQLModel parameterized queries prevent injection
6. **User Isolation**: Every query includes `WHERE user_id = ?` filter

## Performance Considerations

1. **Connection Pooling**: asyncpg pool_size=10, max_overflow=20
2. **Database Indexes**: Index on `user_id` column for fast filtering
3. **Async Operations**: All I/O operations use async/await
4. **Query Optimization**: Select only needed columns, avoid N+1 queries
5. **Caching**: Consider Redis for session caching (future enhancement)

## Alternatives Rejected

1. **Synchronous Python**: Rejected - Constitution requires async
2. **GraphQL**: Rejected - REST is simpler for CRUD operations
3. **MongoDB**: Rejected - Constitution specifies Neon PostgreSQL
4. **Auth0/Clerk**: Rejected - Constitution requires Better Auth
5. **Prisma ORM**: Rejected - Python backend requires Python ORM

## Next Steps

1. ✅ Research complete
2. ⏭️ Create data-model.md with SQLModel schemas
3. ⏭️ Create API contracts in contracts/ directory
4. ⏭️ Create quickstart.md with setup instructions
