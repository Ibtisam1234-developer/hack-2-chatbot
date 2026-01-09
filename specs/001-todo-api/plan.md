# Implementation Plan: Todo API with Authentication

**Branch**: `001-todo-api` | **Date**: 2026-01-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-todo-api/spec.md`

## Summary

Build a secure Todo API using FastAPI that wraps existing CLI functionality, with JWT authentication via Better Auth and user-isolated data storage in Neon PostgreSQL. The system provides 6 REST endpoints (List, Get, Create, Update, Delete, Toggle Completion) with async operations and strict user_id filtering per constitution requirements.

**Key Technical Approach**:
- Preserve existing CLI code and wrap with FastAPI service layer
- Share BETTER_AUTH_SECRET between Next.js and FastAPI for JWT verification
- Use SQLModel for database schema with asyncpg driver for Neon DB
- Implement JWT middleware to extract user_id from `sub` claim
- Enforce user isolation in all database queries

## Technical Context

**Language/Version**: Python 3.11+, TypeScript 5+
**Primary Dependencies**: FastAPI, SQLModel, asyncpg, python-jose (JWT), Better Auth, Next.js 16+, React 19+
**Storage**: Neon PostgreSQL (serverless, PostgreSQL-compatible)
**Testing**: pytest (backend), Jest/React Testing Library (frontend)
**Target Platform**: Web application (Linux/Windows server for backend, browser for frontend)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: <1s list retrieval (100 items), <2s create/update operations, 100+ concurrent users
**Constraints**: <200ms p95 API latency, JWT token validation on every request, user_id filtering mandatory
**Scale/Scope**: Initial deployment for 100-1000 users, ~6 API endpoints, single database table

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Multi-Agent Collaboration ✅

**Requirement**: Leverage specialized sub-agents for focused execution

**Compliance**:
- Database configuration delegated to `neon-schema-manager` agent
- Backend migration delegated to `fastapi-migration-engineer` agent
- Frontend authentication delegated to `nextjs-auth-frontend` agent
- Clear boundaries: DB schema, API layer, UI layer

**Status**: PASS - Plan explicitly delegates to specialized agents per user input

### Principle II: Authentication & Authorization ✅

**Requirement**: Shared BETTER_AUTH_SECRET, JWT sub claim for user_id, token validation on all routes

**Compliance**:
- Single BETTER_AUTH_SECRET in .env shared by Next.js and FastAPI
- JWT middleware extracts user_id from `sub` claim
- All API endpoints protected with JWT validation
- 401 Unauthorized for invalid/missing tokens

**Status**: PASS - Architecture enforces shared secret and JWT protocol

### Principle III: Service Layer Transformation ✅

**Requirement**: Preserve CLI code, wrap with FastAPI, no business logic duplication

**Compliance**:
- Existing CLI code remains in `backend/src/cli/` directory
- FastAPI routes in `backend/src/api/` import and invoke CLI functions
- Service layer acts as HTTP adapter only
- CLI remains independently executable

**Status**: PASS - Architecture preserves CLI and wraps with API layer

### Principle IV: Security: User Isolation ✅

**Requirement**: All queries filter by user_id from JWT sub claim

**Compliance**:
- JWT middleware extracts user_id at request entry point
- All database queries include `WHERE user_id = ?` filter
- SQLModel queries use `.filter(Todo.user_id == user_id)`
- No global queries without explicit filtering

**Status**: PASS - Data model and query patterns enforce user isolation

### Principle V: Async Python Development ✅

**Requirement**: Async/await for all I/O, async route handlers, asyncpg driver

**Compliance**:
- All FastAPI route handlers: `async def endpoint(...)`
- Database operations: `await session.execute(...)`
- SQLModel with asyncpg engine for Neon DB
- No blocking I/O in async contexts

**Status**: PASS - Architecture uses async patterns throughout

### Gate Result: ✅ PASS

All constitution principles satisfied. Proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/001-todo-api/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
│   ├── api-endpoints.yaml
│   └── error-responses.yaml
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   └── todo.py          # SQLModel Todo schema
│   ├── services/
│   │   └── todo_service.py  # Business logic (wraps CLI)
│   ├── api/
│   │   ├── middleware/
│   │   │   └── auth.py      # JWT validation middleware
│   │   ├── routes/
│   │   │   └── todos.py     # FastAPI route handlers
│   │   └── main.py          # FastAPI app initialization
│   ├── cli/
│   │   └── todo_cli.py      # Existing CLI code (preserved)
│   ├── db/
│   │   └── database.py      # Neon DB connection (asyncpg)
│   └── config.py            # Environment variables
├── tests/
│   ├── test_auth.py         # JWT validation tests
│   ├── test_user_isolation.py  # Security tests
│   └── test_todos.py        # API endpoint tests
├── requirements.txt
└── .env.example

frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── dashboard/
│   │   │   └── page.tsx     # Todo list UI
│   │   └── layout.tsx
│   ├── components/
│   │   ├── TodoList.tsx
│   │   ├── TodoItem.tsx
│   │   └── TodoForm.tsx
│   ├── lib/
│   │   ├── auth.ts          # Better Auth configuration
│   │   └── api-client.ts    # API client with JWT
│   └── types/
│       └── todo.ts          # TypeScript types
├── tests/
│   └── components/
└── package.json

.env                         # Shared secrets (not committed)
├── BETTER_AUTH_SECRET       # Shared by Next.js and FastAPI
├── DATABASE_URL             # Neon PostgreSQL connection string
└── NEXTAUTH_URL             # Next.js auth URL
```

**Structure Decision**: Web application structure selected due to separate frontend (Next.js) and backend (FastAPI) requirements. Backend preserves CLI code in dedicated directory per constitution Principle III. Frontend uses Next.js App Router with Better Auth integration.

## Complexity Tracking

> No constitution violations - this section intentionally left empty.

## Phase 0: Research & Technology Decisions

See [research.md](./research.md) for detailed research findings.

**Key Decisions**:
1. **JWT Library**: python-jose for FastAPI JWT verification (industry standard, well-maintained)
2. **Database Driver**: asyncpg for Neon DB (async-native, high performance)
3. **ORM**: SQLModel (Pydantic + SQLAlchemy, type-safe, async support)
4. **Better Auth Plugin**: jwt() plugin for token generation in Next.js
5. **API Client**: fetch with custom wrapper for JWT token attachment

## Phase 1: Data Model & Contracts

### Data Model

See [data-model.md](./data-model.md) for complete entity definitions.

**Core Entity**: Todo
- Primary key: UUID
- Foreign key: user_id (string, from JWT sub claim)
- Fields: title, description, is_completed, created_at, updated_at
- Indexes: user_id (for query performance)

### API Contracts

See [contracts/api-endpoints.yaml](./contracts/api-endpoints.yaml) for OpenAPI specification.

**Endpoints**:
1. `GET /api/todos` - List all todos for authenticated user
2. `GET /api/todos/{id}` - Get specific todo
3. `POST /api/todos` - Create new todo
4. `PUT /api/todos/{id}` - Update todo
5. `DELETE /api/todos/{id}` - Delete todo
6. `PATCH /api/todos/{id}/complete` - Toggle completion status

### Quickstart Guide

See [quickstart.md](./quickstart.md) for setup and development instructions.

## Agent Delegation Strategy

Per constitution Principle I (Multi-Agent Collaboration), implementation will be delegated to specialized agents:

### Phase 1: Infrastructure (@neon-schema-manager)
- Configure Neon PostgreSQL database
- Create Todo table with user_id foreign key
- Set up environment variables (DATABASE_URL, BETTER_AUTH_SECRET)
- Verify asyncpg connection

### Phase 2: Backend Migration (@fastapi-migration-engineer)
- Preserve existing CLI code in backend/src/cli/
- Create SQLModel Todo schema
- Implement JWT middleware for token validation
- Wrap CLI functions with FastAPI route handlers
- Enforce user_id filtering in all queries
- Implement async database operations

### Phase 3: Frontend & Auth (@nextjs-auth-frontend)
- Configure Better Auth with jwt() plugin
- Create authenticated API client with JWT token attachment
- Build Todo UI components (list, form, item)
- Implement optimistic updates for better UX
- Handle authentication errors and token refresh

### Phase 4: Integration (Coordinated)
- Connect frontend to backend API
- End-to-end testing of authentication flow
- Verify user isolation across multiple users
- Performance testing (100+ concurrent users)

## Next Steps

1. ✅ Phase 0 complete: Research findings documented
2. ✅ Phase 1 complete: Data model and contracts defined
3. ⏭️ Run `/sp.tasks` to generate implementation tasks
4. ⏭️ Execute tasks using specialized agents per delegation strategy
