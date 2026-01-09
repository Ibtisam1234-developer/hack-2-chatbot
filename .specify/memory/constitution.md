<!--
Sync Impact Report:
- Version change: [NEW] → 1.0.0
- Modified principles: N/A (initial constitution)
- Added sections: 5 core principles, Architecture & Integration, Development Standards, Governance
- Removed sections: N/A
- Templates requiring updates:
  ✅ spec-template.md - reviewed, aligned with security and authentication requirements
  ✅ plan-template.md - reviewed, constitution check section compatible
  ✅ tasks-template.md - reviewed, task structure supports async Python and security requirements
- Follow-up TODOs: None
-->

# TodoWeb Constitution

## Core Principles

### I. Multi-Agent Collaboration

All complex tasks MUST leverage specialized sub-agents for focused execution. When a task involves multiple domains (frontend, backend, database, testing), delegate to appropriate sub-agents rather than attempting monolithic implementation. Each sub-agent operates with clear boundaries and well-defined interfaces.

**Rationale**: Specialized agents reduce cognitive load, improve code quality through focused expertise, and enable parallel execution of independent tasks.

### II. Authentication & Authorization

Better Auth in Next.js and FastAPI backend MUST share a single `BETTER_AUTH_SECRET` environment variable for JWT token generation and verification. All API endpoints MUST validate JWT tokens and extract the `sub` claim as the authenticated user identifier.

**Non-negotiable rules**:
- Single source of truth for auth secret (`.env` file, never committed)
- JWT `sub` claim contains the user_id
- All protected routes verify token before processing
- Token verification failures return 401 Unauthorized

**Rationale**: Shared secret ensures cryptographic consistency across frontend and backend. Standardizing on the `sub` claim prevents user identifier confusion and simplifies authorization logic.

### III. Service Layer Transformation

When refactoring existing CLI code into FastAPI services, the original CLI logic MUST be preserved and wrapped, not deleted or rewritten. The service layer acts as an adapter that exposes CLI functionality via HTTP endpoints.

**Non-negotiable rules**:
- Original CLI code remains intact and functional
- Service layer imports and invokes CLI functions
- No business logic duplication between CLI and API
- CLI can still be used independently for testing and automation

**Rationale**: Preserving CLI code maintains existing functionality, enables gradual migration, supports multiple interfaces (CLI + API), and reduces regression risk.

### IV. Security: User Isolation

All database queries MUST enforce user_id isolation using the JWT `sub` claim. Every query that reads or modifies user data MUST include a WHERE clause filtering by user_id. No query may access data belonging to other users.

**Non-negotiable rules**:
- Extract user_id from JWT `sub` claim at request entry point
- Pass user_id explicitly to all data access functions
- All SELECT/UPDATE/DELETE queries filter by user_id
- No global queries without explicit admin authorization check
- Audit logs capture user_id for all data modifications

**Rationale**: User isolation prevents unauthorized data access, satisfies privacy requirements, and creates clear security boundaries. Explicit filtering makes security violations immediately visible in code review.

### V. Async Python Development

All database operations, external API calls, and I/O-bound operations MUST use async/await patterns. FastAPI route handlers MUST be async functions. Database clients MUST use async drivers (e.g., asyncpg for PostgreSQL/Neon).

**Non-negotiable rules**:
- All route handlers: `async def endpoint(...)`
- All database queries: `await db.execute(...)`
- All external HTTP calls: `await httpx.get(...)`
- No blocking I/O in async contexts
- Use `asyncio.gather()` for parallel operations

**Rationale**: Async operations maximize throughput under concurrent load, prevent thread blocking, and align with FastAPI's async-first architecture. Neon DB benefits from connection pooling in async contexts.

## Architecture & Integration

### Technology Stack

- **Frontend**: Next.js 16+ with React 19+, TypeScript
- **Backend**: FastAPI (Python 3.11+), async/await
- **Database**: Neon DB (PostgreSQL-compatible), asyncpg driver
- **Authentication**: Better Auth (shared secret)
- **Deployment**: TBD (requires clarification)

### Integration Points

- **Auth Flow**: Next.js Better Auth → JWT token → FastAPI verification → user_id extraction
- **API Communication**: Next.js frontend → FastAPI backend (REST/JSON)
- **Database Access**: FastAPI → Neon DB (async queries with user_id filtering)

## Development Standards

### Code Quality

- TypeScript strict mode enabled for frontend
- Python type hints required for all function signatures
- Linting: ESLint (frontend), Ruff/Black (backend)
- All async functions must handle exceptions appropriately

### Testing Requirements

- Authentication: Test JWT generation, verification, and expiration
- Security: Test user isolation (attempt cross-user data access)
- Service Layer: Test CLI functionality through API endpoints
- Async Operations: Test concurrent request handling

### Security Checklist

- [ ] All API routes validate JWT tokens
- [ ] All database queries filter by user_id
- [ ] BETTER_AUTH_SECRET in .env (not committed)
- [ ] No hardcoded credentials or secrets
- [ ] Input validation on all API endpoints
- [ ] SQL injection prevention (parameterized queries)

## Governance

This constitution supersedes all other development practices and conventions. All code changes, architecture decisions, and feature implementations MUST comply with these principles.

### Amendment Process

1. Propose amendment with rationale and impact analysis
2. Document affected systems and migration requirements
3. Update constitution version (semantic versioning)
4. Propagate changes to dependent templates and documentation
5. Create Architecture Decision Record (ADR) for significant changes

### Compliance Review

- All pull requests MUST verify compliance with constitution principles
- Security principle violations are blocking (cannot merge)
- Architecture violations require explicit justification and approval
- Constitution checks integrated into planning phase (`/sp.plan` command)

### Versioning Policy

- **MAJOR**: Backward-incompatible principle changes or removals
- **MINOR**: New principles added or material expansions
- **PATCH**: Clarifications, wording improvements, non-semantic fixes

**Version**: 1.0.0 | **Ratified**: 2026-01-07 | **Last Amended**: 2026-01-07
