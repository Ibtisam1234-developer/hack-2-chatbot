# Feature Specification: Todo API with Authentication

**Feature Branch**: `001-todo-api`
**Created**: 2026-01-07
**Status**: Draft
**Input**: User description: "Based on our constitution, run /sp.specify to create a technical contract. Detail the 6 required API endpoints (GET, POST, PUT, DELETE, PATCH for completion). Define the Pydantic/SQLModel schemas, specifically mapping the legacy CLI data structure to the new Neon PostgreSQL table. Explicitly define the JWT handshake protocol between Better Auth and FastAPI"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and View Todos (Priority: P1)

As an authenticated user, I need to create new todo items and view my personal todo list so that I can track tasks I need to complete.

**Why this priority**: Core functionality - without the ability to create and view todos, the system has no value. This is the minimum viable product.

**Independent Test**: Can be fully tested by authenticating a user, creating multiple todos, and retrieving the list. Delivers immediate value as a basic task tracker.

**Acceptance Scenarios**:

1. **Given** I am an authenticated user, **When** I create a new todo with a title and optional description, **Then** the todo is saved and appears in my todo list
2. **Given** I am an authenticated user with existing todos, **When** I request my todo list, **Then** I see only my todos (not other users' todos)
3. **Given** I am an authenticated user, **When** I request a specific todo by its identifier, **Then** I see the complete details of that todo if it belongs to me
4. **Given** I am an unauthenticated user, **When** I attempt to create or view todos, **Then** I receive an authentication error

---

### User Story 2 - Update and Delete Todos (Priority: P2)

As an authenticated user, I need to update todo details and delete todos I no longer need so that I can maintain an accurate and current task list.

**Why this priority**: Essential for practical use - users need to correct mistakes, update information, and remove completed or cancelled tasks.

**Independent Test**: Can be tested by creating a todo, modifying its title/description, and then deleting it. Works independently of other features.

**Acceptance Scenarios**:

1. **Given** I am an authenticated user with an existing todo, **When** I update the todo's title or description, **Then** the changes are saved and reflected when I view the todo
2. **Given** I am an authenticated user with an existing todo, **When** I delete the todo, **Then** it no longer appears in my todo list
3. **Given** I am an authenticated user, **When** I attempt to update or delete another user's todo, **Then** I receive an authorization error
4. **Given** I am an authenticated user, **When** I attempt to update or delete a non-existent todo, **Then** I receive a not-found error

---

### User Story 3 - Mark Todos as Complete (Priority: P3)

As an authenticated user, I need to mark todos as complete or incomplete so that I can track my progress and distinguish between pending and finished tasks.

**Why this priority**: Enhances usability - allows users to track completion status without deleting completed items, enabling progress tracking and task history.

**Independent Test**: Can be tested by creating a todo, marking it complete, unmarking it, and verifying the completion status changes. Provides value as a progress tracker.

**Acceptance Scenarios**:

1. **Given** I am an authenticated user with an incomplete todo, **When** I mark the todo as complete, **Then** the todo's completion status is updated and visible in my list
2. **Given** I am an authenticated user with a complete todo, **When** I mark the todo as incomplete, **Then** the todo's completion status is updated to incomplete
3. **Given** I am an authenticated user, **When** I view my todo list, **Then** I can see which todos are complete and which are incomplete
4. **Given** I am an authenticated user, **When** I attempt to change the completion status of another user's todo, **Then** I receive an authorization error

---

### User Story 4 - Secure Authentication Integration (Priority: P1)

As a system, I need to authenticate users via JWT tokens issued by Better Auth and enforce user isolation so that each user can only access their own data.

**Why this priority**: Security foundation - must be implemented alongside P1 user stories to prevent unauthorized access. Non-negotiable per constitution.

**Independent Test**: Can be tested by attempting API requests with valid tokens, invalid tokens, expired tokens, and tokens for different users. Verifies security boundaries.

**Acceptance Scenarios**:

1. **Given** a user has authenticated via Better Auth, **When** they make an API request with a valid JWT token, **Then** the system extracts their user_id and processes the request
2. **Given** a user makes an API request, **When** they provide an invalid or expired JWT token, **Then** the system rejects the request with an authentication error
3. **Given** a user makes an API request, **When** they provide no authentication token, **Then** the system rejects the request with an authentication error
4. **Given** User A has a valid JWT token, **When** they attempt to access User B's todos, **Then** the system prevents access and returns only User A's data

---

### Edge Cases

- What happens when a user attempts to create a todo with an empty title?
- What happens when a user attempts to retrieve a todo that was deleted?
- What happens when a JWT token expires during a long-running session?
- What happens when the database connection is temporarily unavailable?
- What happens when a user attempts to create a todo with extremely long text (title or description)?
- What happens when concurrent requests attempt to update the same todo simultaneously?
- What happens when a user's JWT token contains an invalid or missing user_id claim?

## Requirements *(mandatory)*

### Functional Requirements

#### Todo Management

- **FR-001**: System MUST allow authenticated users to create new todo items with a title (required) and description (optional)
- **FR-002**: System MUST allow authenticated users to retrieve a list of all their todo items
- **FR-003**: System MUST allow authenticated users to retrieve a specific todo item by its unique identifier
- **FR-004**: System MUST allow authenticated users to update the title and description of their existing todo items
- **FR-005**: System MUST allow authenticated users to delete their existing todo items
- **FR-006**: System MUST allow authenticated users to mark todo items as complete or incomplete
- **FR-007**: System MUST persist all todo data so that it survives application restarts
- **FR-008**: System MUST assign a unique identifier to each todo item upon creation

#### Authentication & Authorization

- **FR-009**: System MUST validate JWT tokens on every API request to protected endpoints
- **FR-010**: System MUST extract the user_id from the JWT token's `sub` claim for all authenticated requests
- **FR-011**: System MUST reject requests with missing, invalid, or expired JWT tokens
- **FR-012**: System MUST verify JWT tokens using the shared secret from Better Auth
- **FR-013**: System MUST return appropriate HTTP status codes for authentication failures (401 Unauthorized)

#### Security & Data Isolation

- **FR-014**: System MUST enforce user isolation - users can only access their own todo items
- **FR-015**: System MUST filter all database queries by the authenticated user's user_id
- **FR-016**: System MUST prevent users from viewing, updating, or deleting other users' todo items
- **FR-017**: System MUST return appropriate HTTP status codes for authorization failures (403 Forbidden or 404 Not Found)
- **FR-018**: System MUST validate all user input to prevent injection attacks

#### Data Migration

- **FR-019**: System MUST preserve existing CLI todo data structure during migration to database
- **FR-020**: System MUST map legacy CLI data fields to corresponding database table columns
- **FR-021**: System MUST maintain data integrity during the CLI-to-API transformation

### Key Entities

- **Todo Item**: Represents a single task or item to be completed
  - Unique identifier (system-generated)
  - Title (required, user-provided text)
  - Description (optional, user-provided text)
  - Completion status (boolean: complete or incomplete)
  - Owner (user_id of the user who created it)
  - Creation timestamp (when the todo was created)
  - Last modified timestamp (when the todo was last updated)

- **User**: Represents an authenticated user (managed by Better Auth)
  - User identifier (from JWT sub claim)
  - Relationship: One user has many todos

### API Endpoints Required

The system MUST provide the following HTTP endpoints for todo operations:

1. **List Todos**: Retrieve all todos for the authenticated user
2. **Get Todo**: Retrieve a specific todo by identifier
3. **Create Todo**: Create a new todo item
4. **Update Todo**: Update an existing todo's title and/or description
5. **Delete Todo**: Remove a todo item
6. **Toggle Completion**: Mark a todo as complete or incomplete (partial update)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Authenticated users can create a new todo and see it in their list within 2 seconds
- **SC-002**: Users can retrieve their complete todo list (up to 100 items) in under 1 second
- **SC-003**: System correctly isolates user data - 100% of requests return only the authenticated user's todos
- **SC-004**: System rejects 100% of requests with invalid or missing authentication tokens
- **SC-005**: Users can update or delete their todos with changes reflected immediately (within 1 second)
- **SC-006**: System handles at least 100 concurrent authenticated users without performance degradation
- **SC-007**: All legacy CLI todo data is successfully migrated to the database with zero data loss
- **SC-008**: API responses include appropriate HTTP status codes (200, 201, 400, 401, 403, 404, 500) for all scenarios

## Assumptions

1. **Authentication Provider**: Better Auth is already configured and issuing JWT tokens with a `sub` claim containing the user_id
2. **Shared Secret**: The `BETTER_AUTH_SECRET` environment variable is available to both Next.js and FastAPI applications
3. **Legacy CLI Format**: The existing CLI todo data structure includes at minimum: title, description, and completion status
4. **Database Schema**: The database table will be created during the planning/implementation phase
5. **Token Expiration**: JWT tokens have a reasonable expiration time (assumed 1-24 hours) managed by Better Auth
6. **User Registration**: User registration and initial authentication are handled by Better Auth (out of scope for this feature)
7. **Todo Ordering**: Todos will be returned in creation order (newest first) unless otherwise specified
8. **Input Limits**: Title limited to 200 characters, description limited to 2000 characters (reasonable defaults)

## Dependencies

- **Better Auth**: Must be configured and operational for JWT token generation
- **Shared Secret**: `BETTER_AUTH_SECRET` must be configured in environment variables for both frontend and backend
- **Database**: Neon PostgreSQL database must be provisioned and accessible
- **Legacy CLI**: Existing CLI code must be available for wrapping/migration

## Out of Scope

- User registration and account management (handled by Better Auth)
- Todo sharing or collaboration features
- Todo categories, tags, or labels
- Todo due dates or reminders
- Todo prioritization or sorting (beyond creation order)
- Bulk operations (delete all, mark all complete)
- Todo search or filtering
- Real-time synchronization or websockets
- Mobile-specific features
- Offline support

## Technical Contracts Note

Detailed technical specifications including:
- API endpoint contracts (HTTP methods, paths, request/response schemas)
- Pydantic/SQLModel data models
- Database table schema and column mappings
- JWT verification protocol and middleware implementation
- Error response formats

These will be defined during the planning phase (`/sp.plan`) and documented in the `specs/001-todo-api/contracts/` directory.
