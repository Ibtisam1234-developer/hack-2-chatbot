---
id: 001
title: Initialize Neon PostgreSQL Database for Todo API
stage: implementation
date: 2026-01-09
surface: agent
model: claude-sonnet-4-5
feature: 001-todo-api
branch: not-a-git-repo
user: User
command: database-initialization
labels: ["database", "neon", "sqlmodel", "multi-tenant", "serverless"]
links:
  spec: E:\todoweb\specs\001-todo-api\spec.md
  plan: E:\todoweb\specs\001-todo-api\plan.md
  data_model: E:\todoweb\specs\001-todo-api\data-model.md
  ticket: null
  adr: null
  pr: null
files:
  - E:\todoweb\backend\src\db\__init__.py
  - E:\todoweb\backend\src\db\connection.py
  - E:\todoweb\backend\src\db\models.py
  - E:\todoweb\backend\src\db\verify.py
  - E:\todoweb\backend\src\db\README.md
  - E:\todoweb\backend\src\db\SETUP_COMPLETE.md
tests:
  - Database verification script (verify.py)
  - Health check function (check_database_health)
  - Connection validation with pool_pre_ping
---

## Prompt

Initialize the Neon PostgreSQL database for the Todo API project.

**Context:**
- Project: Todo API with JWT authentication
- Database: Neon Serverless PostgreSQL
- Auth: Better Auth manages user table
- Multi-tenant: All queries must filter by user_id

**Tasks to complete:**
1. Read the data model from specs/001-todo-api/data-model.md
2. Create the database connection configuration in backend/src/db/connection.py with:
   - Serverless-optimized settings (pool_pre_ping=True)
   - AsyncEngine with asyncpg driver
   - Connection pooling for Neon
3. Create the Todo SQLModel schema in backend/src/db/models.py with:
   - id (UUID, primary key)
   - user_id (String, indexed, required)
   - title (String, required)
   - description (String, optional)
   - completed (Boolean, default False)
   - created_at (DateTime)
   - updated_at (DateTime)
4. Ensure Better Auth compatibility (user table managed by Better Auth)
5. Create database initialization script in backend/src/db/__init__.py

**Environment:**
- DATABASE_URL is already in .env file (needs to be filled by user)
- BETTER_AUTH_SECRET is already in .env file (needs to be filled by user)

**Success criteria:**
- Database connection module created with Neon-optimized settings
- Todo model created with proper multi-tenant isolation (user_id field)
- All files follow the architecture defined in specs/001-todo-api/plan.md
- No migration commands needed yet (Better Auth will handle user table)

## Response

### Summary

Successfully initialized the Neon PostgreSQL database module for the Todo API with full multi-tenant isolation, serverless optimization, and Better Auth compatibility. Created 6 comprehensive files implementing async database operations with SQLModel.

### Files Created

1. **connection.py** (7,276 bytes)
   - AsyncEngine with asyncpg driver for Neon PostgreSQL
   - pool_pre_ping=True for serverless cold start handling
   - Connection pooling optimized for serverless (pool_size=5, max_overflow=10)
   - Session management with FastAPI dependency injection
   - Health check and retry logic with exponential backoff

2. **models.py** (6,119 bytes)
   - Todo: Database model with all fields including user_id (REQUIRED)
   - TodoCreate: Request model for creating todos
   - TodoUpdate: Request model for partial updates
   - TodoResponse: Response model with all fields
   - All models enforce multi-tenant isolation

3. **__init__.py** (3,850 bytes)
   - Package initialization and exports
   - init_database(): Creates tables and composite indexes
   - cleanup_database(): Graceful shutdown
   - get_session(): FastAPI dependency for database sessions

4. **verify.py** (5,477 bytes)
   - Database verification script
   - Tests connectivity, schema, and indexes
   - Provides detailed status output
   - Usage: python -m backend.src.db.verify

5. **README.md** (9,011 bytes)
   - Comprehensive documentation
   - Usage examples for FastAPI routes
   - Security considerations and best practices
   - Performance optimization tips
   - Troubleshooting guide

6. **SETUP_COMPLETE.md** (10,409 bytes)
   - Complete setup summary
   - Next steps and integration guide
   - Security checklist
   - Architecture decisions and rationale

### Constitutional Compliance

✅ **Multi-Tenant Isolation (Principle IV)**
- All tables include user_id: str column (REQUIRED)
- user_id is indexed for query performance
- All queries MUST filter by user_id
- User ID extracted from JWT sub claim (never from client input)

✅ **SQLModel Exclusive**
- All models use SQLModel (Pydantic + SQLAlchemy)
- No raw SQLAlchemy models
- Type-safe database interactions

✅ **Neon Serverless Optimization**
- pool_pre_ping=True for cold start handling
- Small connection pool (5 connections)
- Connection recycling (3600 seconds)
- Async/await throughout

✅ **Better Auth Compatibility**
- No conflicts with Better Auth tables
- user_id references Better Auth's user table
- No foreign key constraints (Better Auth manages users)

### Database Schema

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

-- Indexes for performance
CREATE INDEX ix_todos_user_id ON todos(user_id);
CREATE INDEX idx_todos_user_completed ON todos(user_id, is_completed);
```

### Key Technical Decisions

1. **AsyncEngine with asyncpg**: Chosen for async/await support and best performance with Neon
2. **pool_pre_ping=True**: Critical for serverless cold start handling
3. **Small pool size (5)**: Optimized for serverless vs traditional databases
4. **UUID primary keys**: Prevents enumeration attacks, globally unique
5. **Composite index**: Optimizes "show my incomplete todos" queries

### Next Steps

1. Configure DATABASE_URL in .env file with Neon connection string
2. Run verification script: `python -m backend.src.db.verify`
3. Integrate with FastAPI application (startup/shutdown events)
4. Implement JWT middleware for user_id extraction
5. Create API routes with user isolation

### Validation

- [x] All tables include user_id: str column
- [x] user_id is indexed for performance
- [x] SQLModel used exclusively
- [x] Connection includes pool_pre_ping=True
- [x] No naming conflicts with Better Auth tables
- [x] Environment variables used for DATABASE_URL
- [x] Error handling for connection failures
- [x] Type hints complete and correct
- [x] Comprehensive documentation provided

### Outcome

Database module is complete and ready for use. All constitutional requirements met. User needs to:
1. Fill in DATABASE_URL in .env file
2. Run verification script to create tables
3. Proceed with JWT middleware and API route implementation

No blockers or issues encountered. Architecture follows the plan defined in specs/001-todo-api/plan.md.
