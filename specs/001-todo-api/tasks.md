---

description: "Task list template for feature implementation"
---

# Tasks: Todo API with Authentication

**Input**: Design documents from `/specs/001-todo-api/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`
- Paths shown below follow web application structure from plan.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create backend directory structure (backend/src/models/, backend/src/services/, backend/src/api/, backend/src/cli/, backend/src/db/, backend/tests/)
- [ ] T002 Create frontend directory structure (frontend/src/app/, frontend/src/components/, frontend/src/lib/, frontend/src/types/, frontend/tests/)
- [ ] T003 [P] Initialize Python project with requirements.txt in backend/ (FastAPI, SQLModel, asyncpg, python-jose, python-dotenv, pydantic-settings)
- [ ] T004 [P] Initialize Node.js project with package.json in frontend/ (Next.js 16+, React 19+, Better Auth, TypeScript 5+)
- [ ] T005 [P] Create .env.example file in project root with BETTER_AUTH_SECRET, DATABASE_URL, API_PORT, CORS_ORIGINS, NEXT_PUBLIC_API_URL, NEXTAUTH_URL placeholders
- [ ] T006 [P] Create backend/.env.example with backend-specific variables
- [ ] T007 [P] Create frontend/.env.example with frontend-specific variables

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Create Neon PostgreSQL database project and obtain connection string. Validation: Verify connection string format is postgresql://user:pass@host.neon.tech/db
- [ ] T009 Generate BETTER_AUTH_SECRET using openssl rand -base64 32 and add to .env file. Validation: Verify secret is exactly 44 characters (base64 encoded 32 bytes)
- [ ] T010 Create backend/src/config.py to load environment variables using pydantic-settings. Validation: Verify BETTER_AUTH_SECRET and DATABASE_URL are loaded correctly
- [ ] T011 Create backend/src/db/database.py with async SQLAlchemy engine using asyncpg driver. Validation: Verify pool_pre_ping=True, pool_size=10, max_overflow=20, pool_recycle=3600
- [ ] T012 Create database initialization script backend/src/db/init_db.py to create tables using SQLModel.metadata.create_all. Validation: Run script and verify todos table exists in Neon database
- [ ] T013 Run Better Auth CLI migration command: npx @better-auth/cli migrate in frontend/ directory. Validation: Verify Better Auth tables (user, session, account, verification) are created in Neon database
- [ ] T014 Create backend/src/api/middleware/auth.py with verify_token() function using python-jose. Validation: Verify JWT verification middleware returns 401 if secret is mismatched
- [ ] T015 Create backend/src/api/middleware/auth.py with get_current_user_id() dependency that extracts user_id from JWT sub claim. Validation: Verify middleware returns 401 if sub claim is missing
- [ ] T016 Create backend/src/api/main.py with FastAPI app initialization and CORS middleware. Validation: Verify CORS allows http://localhost:3000 origin
- [ ] T017 Add health check endpoint GET /health in backend/src/api/main.py. Validation: curl http://localhost:8000/health returns {"status": "healthy"}
- [ ] T018 [P] Preserve existing CLI code by creating backend/src/cli/todo_cli.py with placeholder functions (create_todo, list_todos, get_todo, update_todo, delete_todo, toggle_completion). Validation: Verify CLI functions can be imported and called independently
- [ ] T019 Create backend/src/db/session.py with get_session() dependency for database sessions. Validation: Verify async context manager properly closes sessions

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 + 4 - Create/View Todos + Authentication (Priority: P1) 🎯 MVP

**Goal**: Authenticated users can create new todos and view their personal todo list with JWT authentication

**Independent Test**: Authenticate a user, create multiple todos, retrieve the list. Verify user isolation (User A cannot see User B's todos).

### Implementation for User Story 1 + 4

- [ ] T020 [P] [US1] Create backend/src/models/todo.py with TodoBase, Todo, TodoCreate, TodoUpdate, TodoResponse SQLModel schemas per data-model.md. Validation: Verify title field has min_length=1, max_length=200 constraints
- [ ] T021 [P] [US1] Create database migration to add todos table with indexes (user_id, user_id+is_completed composite). Validation: Run migration and verify indexes exist using \d todos in psql
- [ ] T022 [US1] Create backend/src/services/todo_service.py with create_todo() function that wraps CLI and adds user_id. Validation: Verify function adds user_id from parameter and calls CLI create_todo()
- [ ] T023 [US1] Create backend/src/services/todo_service.py with get_user_todos() function that filters by user_id. Validation: Verify query includes WHERE user_id = ? filter
- [ ] T024 [US1] Create backend/src/services/todo_service.py with get_user_todo() function that filters by todo_id AND user_id. Validation: Verify query returns None if user_id doesn't match
- [ ] T025 [US1] Create backend/src/api/routes/todos.py with POST /api/todos endpoint using get_current_user_id dependency. Validation: Verify endpoint returns 401 without valid JWT token
- [ ] T026 [US1] Create backend/src/api/routes/todos.py with GET /api/todos endpoint using get_current_user_id dependency. Validation: Verify endpoint returns only todos for authenticated user
- [ ] T027 [US1] Create backend/src/api/routes/todos.py with GET /api/todos/{id} endpoint using get_current_user_id dependency. Validation: Verify endpoint returns 404 if todo belongs to different user
- [ ] T028 [US1] Register todos router in backend/src/api/main.py. Validation: Verify all 3 endpoints are accessible at /api/todos paths
- [ ] T029 [P] [US4] Create frontend/src/lib/auth.ts with Better Auth configuration using jwt() plugin. Validation: Verify BETTER_AUTH_SECRET matches backend .env value
- [ ] T030 [P] [US4] Configure Better Auth jwt() plugin with expiresIn: "7d", algorithm: "HS256", issuer: "todoweb", audience: "todoweb-api". Validation: Verify generated JWT tokens contain sub, iat, exp, iss, aud claims
- [ ] T031 [US4] Create frontend/src/lib/api-client.ts with apiClient() function that attaches JWT token to Authorization header. Validation: Verify function redirects to /login on 401 response
- [ ] T032 [US4] Create frontend/src/lib/api-client.ts with typed API functions (createTodo, listTodos, getTodo). Validation: Verify functions use apiClient() and return typed responses
- [ ] T033 [P] [US1] Create frontend/src/types/todo.ts with Todo, TodoCreate, TodoUpdate TypeScript interfaces matching backend schemas. Validation: Verify types match OpenAPI schema in contracts/api-endpoints.yaml
- [ ] T034 [P] [US1] Create frontend/src/components/TodoForm.tsx with form for creating todos (title, description fields). Validation: Verify form validates title is required and max 200 characters
- [ ] T035 [P] [US1] Create frontend/src/components/TodoItem.tsx to display a single todo with title, description, completion status. Validation: Verify component displays all todo fields correctly
- [ ] T036 [US1] Create frontend/src/components/TodoList.tsx to display list of todos using TodoItem components. Validation: Verify list updates when todos are added
- [ ] T037 [US1] Create frontend/src/app/dashboard/page.tsx with TodoList and TodoForm components. Validation: Verify page is protected (redirects to /login if not authenticated)
- [ ] T038 [US1] Implement todo creation in TodoForm using createTodo() API function. Validation: Verify new todo appears in list immediately after creation
- [ ] T039 [US1] Implement todo list fetching in dashboard page using listTodos() API function. Validation: Verify only authenticated user's todos are displayed

**Checkpoint**: At this point, User Story 1 (Create/View) and User Story 4 (Authentication) should be fully functional and testable independently

---

## Phase 4: User Story 2 - Update and Delete Todos (Priority: P2)

**Goal**: Authenticated users can update todo details and delete todos they no longer need

**Independent Test**: Create a todo, modify its title/description, then delete it. Verify changes are saved and todo is removed.

### Implementation for User Story 2

- [ ] T040 [US2] Create backend/src/services/todo_service.py with update_todo() function that filters by todo_id AND user_id. Validation: Verify function returns None if user_id doesn't match
- [ ] T041 [US2] Create backend/src/services/todo_service.py with delete_todo() function that filters by todo_id AND user_id. Validation: Verify function returns False if user_id doesn't match
- [ ] T042 [US2] Create backend/src/api/routes/todos.py with PUT /api/todos/{id} endpoint using get_current_user_id dependency. Validation: Verify endpoint returns 404 if todo belongs to different user
- [ ] T043 [US2] Create backend/src/api/routes/todos.py with DELETE /api/todos/{id} endpoint using get_current_user_id dependency. Validation: Verify endpoint returns 404 if todo belongs to different user
- [ ] T044 [US2] Add updateTodo() and deleteTodo() functions to frontend/src/lib/api-client.ts. Validation: Verify functions handle 404 responses appropriately
- [ ] T045 [US2] Add edit button and inline editing to frontend/src/components/TodoItem.tsx. Validation: Verify edited todo updates in list after save
- [ ] T046 [US2] Add delete button to frontend/src/components/TodoItem.tsx with confirmation dialog. Validation: Verify todo is removed from list after deletion
- [ ] T047 [US2] Implement optimistic updates in TodoList for update operations. Validation: Verify UI updates immediately before API response

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Mark Todos as Complete (Priority: P3)

**Goal**: Authenticated users can mark todos as complete or incomplete to track progress

**Independent Test**: Create a todo, mark it complete, unmark it, verify completion status changes are persisted.

### Implementation for User Story 3

- [ ] T048 [US3] Create backend/src/services/todo_service.py with toggle_completion() function that filters by todo_id AND user_id. Validation: Verify function toggles is_completed boolean and updates updated_at timestamp
- [ ] T049 [US3] Create backend/src/api/routes/todos.py with PATCH /api/todos/{id}/complete endpoint using get_current_user_id dependency. Validation: Verify endpoint returns 404 if todo belongs to different user
- [ ] T050 [US3] Add toggleCompletion() function to frontend/src/lib/api-client.ts. Validation: Verify function sends PATCH request to correct endpoint
- [ ] T051 [US3] Add checkbox to frontend/src/components/TodoItem.tsx for toggling completion status. Validation: Verify checkbox reflects current is_completed state
- [ ] T052 [US3] Implement optimistic updates in TodoItem for completion toggle. Validation: Verify checkbox updates immediately before API response
- [ ] T053 [US3] Add visual styling to TodoItem to distinguish completed todos (strikethrough, opacity). Validation: Verify completed todos are visually distinct

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T054 [P] Add error handling to all backend endpoints with appropriate HTTP status codes (400, 401, 404, 422, 500). Validation: Verify error responses match OpenAPI schema in contracts/api-endpoints.yaml
- [ ] T055 [P] Add input validation to all backend endpoints using Pydantic models. Validation: Verify empty title returns 422 with validation error details
- [ ] T056 [P] Add loading states to all frontend components during API calls. Validation: Verify loading indicators appear during network requests
- [ ] T057 [P] Add error toast notifications to frontend for API errors. Validation: Verify user sees error message when API call fails
- [ ] T058 [P] Add empty state to TodoList when no todos exist. Validation: Verify helpful message appears when list is empty
- [ ] T059 [P] Add sorting to todo list (newest first) in backend query. Validation: Verify todos are ordered by created_at DESC
- [ ] T060 [P] Create backend/tests/test_auth.py with JWT validation tests (valid token, expired token, invalid signature, missing sub claim). Validation: All tests pass with pytest
- [ ] T061 [P] Create backend/tests/test_user_isolation.py with security tests (User A cannot access User B's todos). Validation: All tests pass with pytest
- [ ] T062 [P] Create backend/tests/test_todos.py with API endpoint tests for all 6 endpoints. Validation: All tests pass with pytest
- [ ] T063 [P] Add TypeScript type checking to frontend build process. Validation: npm run build completes without type errors
- [ ] T064 [P] Add ESLint to frontend with Next.js config. Validation: npm run lint completes without errors
- [ ] T065 [P] Add Python linting (Ruff/Black) to backend. Validation: ruff check and black --check complete without errors
- [ ] T066 Create README.md with setup instructions based on quickstart.md. Validation: New developer can follow README to set up project
- [ ] T067 Run quickstart.md validation by following all setup steps. Validation: Both backend and frontend start successfully and can create/view todos

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User Story 1 + 4 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - Depends on US1 for testing but independently implementable
  - User Story 3 (P3): Can start after Foundational - Depends on US1 for testing but independently implementable
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 + 4 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independently testable (create todo first, then update/delete)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independently testable (create todo first, then toggle)

### Within Each User Story

- Models before services
- Services before endpoints
- Backend endpoints before frontend API client
- API client before UI components
- Core implementation before integration

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all models for User Story 1 together:
Task: "Create backend/src/models/todo.py with SQLModel schemas"
Task: "Create frontend/src/types/todo.ts with TypeScript interfaces"

# Launch all UI components for User Story 1 together:
Task: "Create frontend/src/components/TodoForm.tsx"
Task: "Create frontend/src/components/TodoItem.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 4 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 + 4 (Create/View + Authentication)
4. **STOP and VALIDATE**: Test User Story 1 + 4 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 + 4 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 + 4 (Create/View + Auth)
   - Developer B: User Story 2 (Update/Delete)
   - Developer C: User Story 3 (Toggle Completion)
3. Stories complete and integrate independently

### Agent Delegation Strategy

Per constitution Principle I (Multi-Agent Collaboration):

1. **@neon-schema-manager**: T008-T013, T021 (database setup, migrations)
2. **@fastapi-migration-engineer**: T014-T019, T020-T028, T040-T043, T048-T049, T054-T055, T060-T062, T065 (backend implementation)
3. **@nextjs-auth-frontend**: T029-T039, T044-T047, T050-T053, T056-T059, T063-T064 (frontend implementation)
4. **Coordinated**: T066-T067 (documentation and validation)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Summary

**Total Tasks**: 67
- Phase 1 (Setup): 7 tasks
- Phase 2 (Foundational): 12 tasks
- Phase 3 (US1 + US4 - P1): 20 tasks
- Phase 4 (US2 - P2): 8 tasks
- Phase 5 (US3 - P3): 6 tasks
- Phase 6 (Polish): 14 tasks

**Parallel Opportunities**: 28 tasks marked [P] can run in parallel within their phase

**Independent Test Criteria**:
- US1 + US4: Authenticate, create todos, view list, verify user isolation
- US2: Create todo, update it, delete it, verify changes persist
- US3: Create todo, toggle completion, verify status changes

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1 + 4) = 39 tasks
