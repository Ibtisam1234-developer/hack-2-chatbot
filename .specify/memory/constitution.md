<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.1.0
- Modified principles: N/A
- Added sections:
  - Principle VI: Stateless Architecture
  - Principle VII: Tool-Only AI Access (MCP)
  - Principle VIII: AI Audit Trail
  - Architecture section: AI Integration subsection
- Removed sections: N/A
- Templates requiring updates:
  ✅ spec-template.md - reviewed, compatible with AI chatbot requirements
  ✅ plan-template.md - reviewed, constitution check section compatible
  ✅ tasks-template.md - reviewed, task structure supports AI integration tasks
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

### VI. Stateless Architecture

The server MUST be horizontally scalable with no local session storage. All state MUST be persisted externally (database, cache) so that any server instance can handle any request. No in-memory session data, no local file caches, no instance-specific state.

**Non-negotiable rules**:
- No in-memory session storage (use database or Redis)
- No local file system for user data or chat history
- All server instances MUST be interchangeable
- Load balancer can route any request to any instance
- Server restarts MUST NOT lose user state

**Rationale**: Horizontal scalability enables elastic scaling under load, zero-downtime deployments, and fault tolerance. Stateless servers simplify infrastructure and eliminate single points of failure.

### VII. Tool-Only AI Access (MCP)

The AI Agent MUST interact with tasks and user data ONLY via Model Context Protocol (MCP) tools. Direct database access from AI logic is FORBIDDEN. All AI capabilities are exposed through well-defined tool interfaces.

**Non-negotiable rules**:
- AI Agent uses MCP tools exclusively for data operations
- No direct SQL queries from AI agent code
- All tool calls are validated and authorized
- Tools enforce user isolation (user_id from JWT)
- Tool responses are structured and predictable

**Rationale**: MCP tools create a security boundary between AI and data. Tools can enforce authorization, validate inputs, and audit actions. This prevents prompt injection from bypassing security controls.

### VIII. AI Audit Trail

Every AI action (tool call) and response MUST be logged in the `Message` table. The audit trail captures the full conversation context, tool invocations, and AI responses for debugging, compliance, and user transparency.

**Non-negotiable rules**:
- All user messages logged with timestamp and user_id
- All AI responses logged with model identifier
- All tool calls logged with parameters and results
- Conversation threads linked via conversation_id
- Logs retained per data retention policy

**Rationale**: Audit trails enable debugging AI behavior, detecting misuse, satisfying compliance requirements, and providing users visibility into AI actions. Complete logging is essential for responsible AI deployment.

## Architecture & Integration

### Technology Stack

- **Frontend**: Next.js 16+ with React 19+, TypeScript
- **Backend**: FastAPI (Python 3.11+), async/await
- **Database**: Neon DB (PostgreSQL-compatible), asyncpg driver
- **Authentication**: Better Auth (shared secret)
- **AI Logic**: OpenAI Agents SDK (Stateless Runner)
- **AI Communication**: Model Context Protocol (MCP) for tool use
- **Deployment**: TBD (requires clarification)

### Integration Points

- **Auth Flow**: Next.js Better Auth → JWT token → FastAPI verification → user_id extraction
- **API Communication**: Next.js frontend → FastAPI backend (REST/JSON)
- **Database Access**: FastAPI → Neon DB (async queries with user_id filtering)
- **AI Integration**: Frontend → FastAPI → OpenAI Agents SDK → MCP Tools → Database

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
- AI Tools: Test MCP tool authorization and user isolation
- Audit Trail: Test message logging completeness and accuracy

### Security Checklist

- [ ] All API routes validate JWT tokens
- [ ] All database queries filter by user_id
- [ ] BETTER_AUTH_SECRET in .env (not committed)
- [ ] No hardcoded credentials or secrets
- [ ] Input validation on all API endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] AI tools enforce user_id isolation from JWT
- [ ] All AI tool calls logged to Message table
- [ ] No direct database access from AI agent code
- [ ] Server stores no local session state

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

**Version**: 1.1.0 | **Ratified**: 2026-01-07 | **Last Amended**: 2026-01-11
