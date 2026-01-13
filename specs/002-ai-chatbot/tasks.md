# Tasks: AI Chatbot Integration

**Input**: Design documents from `/specs/002-ai-chatbot/`
**Prerequisites**: plan.md (required), spec.md (required), data-model.md, contracts/, research.md, quickstart.md

**Tests**: Tests are NOT explicitly requested in the feature specification. Test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `app/`, `components/`, `lib/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and database schema

- [x] T001 [P] Add openai-agents and fastmcp to backend/requirements.txt
- [x] T002 [P] Add @openai/chatkit to package.json via npm install
- [x] T003 Create Conversation SQLModel in backend/src/models/conversation.py per data-model.md
- [x] T004 Create Message SQLModel in backend/src/models/message.py per data-model.md
- [x] T005 Run SQLModel migrations to create conversations and messages tables in Neon DB
- [x] T006 Add OPENAI_API_KEY and OPENAI_MODEL to backend/.env.example

**Checkpoint**: Database tables created, dependencies installed

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Initialize FastMCP server in backend/src/mcp/server.py with task-tools name
- [x] T008 Create verify_task_ownership helper in backend/src/mcp/tools/task_tools.py per mcp-ownership-verification skill
- [x] T009 [P] Implement add_task MCP tool in backend/src/mcp/tools/task_tools.py per contracts/mcp-tools.md
- [x] T010 [P] Implement list_tasks MCP tool in backend/src/mcp/tools/task_tools.py per contracts/mcp-tools.md
- [x] T011 [P] Implement complete_task MCP tool in backend/src/mcp/tools/task_tools.py per contracts/mcp-tools.md
- [x] T012 Mount FastMCP server in FastAPI app in backend/src/api/main.py
- [x] T013 Create get_conversation_history helper in backend/src/services/chat_service.py per stateless-memory-management skill
- [x] T014 Create save_chat_exchange helper in backend/src/services/chat_service.py to persist user and assistant messages
- [x] T015 Create agent_service.py in backend/src/services/ with OpenAI Runner wrapper and system prompt from contracts/mcp-tools.md

**Checkpoint**: MCP tools functional, chat service helpers ready, agent configured

---

## Phase 3: User Story 1 - Chat with AI to Manage Tasks (Priority: P1) 🎯 MVP

**Goal**: Users can send messages to AI and manage tasks via natural language

**Independent Test**: Send "Add a task to buy groceries" and verify task appears in task list

### Implementation for User Story 1

- [x] T016 [US1] Create ChatRequest and ChatResponse Pydantic models in backend/src/api/schemas/chat.py per contracts/chat-api.yaml
- [x] T017 [US1] Implement create_conversation helper in backend/src/services/chat_service.py to auto-generate title from first message
- [x] T018 [US1] Implement POST /api/{user_id}/chat endpoint in backend/src/api/routes/chat.py per contracts/chat-api.yaml
- [x] T019 [US1] Wire chat route: validate JWT, fetch history, call agent, save exchange, return response
- [x] T020 [US1] Register chat router in backend/src/api/main.py
- [x] T021 [US1] Create chat-client.ts in lib/ with sendMessage function that calls POST /api/{user_id}/chat
- [x] T022 [US1] Create ChatInterface.tsx component in components/ using @openai/chatkit
- [x] T023 [US1] Create app/chat/page.tsx with ChatInterface component and authentication guard
- [x] T024 [US1] Add Chat link to dashboard navigation in app/dashboard/page.tsx

**Checkpoint**: User Story 1 complete - users can chat with AI and manage tasks

---

## Phase 4: User Story 2 - Continue Existing Conversations (Priority: P2)

**Goal**: Users can continue previous conversations with maintained context

**Independent Test**: Start conversation, leave, return, send follow-up referencing previous context

### Implementation for User Story 2

- [x] T025 [US2] Update chat-client.ts to accept optional conversation_id parameter
- [x] T026 [US2] Create ConversationList.tsx component in components/ to display user's conversations
- [x] T027 [US2] Implement GET /api/{user_id}/conversations endpoint in backend/src/api/routes/chat.py
- [x] T028 [US2] Update ChatInterface.tsx to support selecting existing conversation from ConversationList
- [x] T029 [US2] Update app/chat/page.tsx to show conversation sidebar and handle conversation selection

**Checkpoint**: User Story 2 complete - users can continue existing conversations

---

## Phase 5: User Story 3 - View Conversation History (Priority: P3)

**Goal**: Users can view past conversations and full message history

**Independent Test**: Have a conversation, navigate to view full message history

### Implementation for User Story 3

- [x] T030 [US3] Implement GET /api/{user_id}/conversations/{conversation_id} endpoint in backend/src/api/routes/chat.py
- [x] T031 [US3] Create MessageBubble.tsx component in components/ with role-based styling (user vs assistant)
- [x] T032 [US3] Update ChatInterface.tsx to load and display full message history when conversation selected
- [x] T033 [US3] Add timestamps to message display in MessageBubble.tsx

**Checkpoint**: User Story 3 complete - users can view conversation history

---

## Phase 6: User Story 4 - AI Actions are Auditable (Priority: P3)

**Goal**: Users can see what tools the AI called and their results

**Independent Test**: Ask AI to create task, verify response shows tool call info

### Implementation for User Story 4

- [x] T034 [US4] Update MessageBubble.tsx to display tool_calls array when present on assistant messages
- [x] T035 [US4] Create ToolCallDisplay.tsx component in components/ to render tool name, arguments, and result
- [x] T036 [US4] Style tool call display with collapsible details for arguments/results

**Checkpoint**: User Story 4 complete - users can see AI tool calls

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Production readiness and deployment configuration

- [x] T037 [P] Add loading state to ChatInterface.tsx while waiting for AI response
- [x] T038 [P] Add error handling to chat-client.ts for network failures and 401 redirects
- [x] T039 [P] Add input validation to ChatInterface.tsx (non-empty message)
- [x] T040 N/A - Using OpenRouter via LiteLLM (no domain allowlist needed)
- [x] T041 Update README.md with chat feature documentation and quickstart reference
- [ ] T042 Run quickstart.md validation checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1): Can start after Foundational
  - US2 (P2): Can start after Foundational (independent of US1)
  - US3 (P3): Can start after Foundational (independent of US1/US2)
  - US4 (P3): Can start after Foundational (independent of US1/US2/US3)
- **Polish (Phase 7)**: Depends on US1 minimum; ideally all stories complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - MVP
- **User Story 2 (P2)**: Enhances US1 but independently testable
- **User Story 3 (P3)**: Enhances US1/US2 but independently testable
- **User Story 4 (P3)**: Enhances US1 but independently testable

### Within Each Phase

- Models before services
- Services before endpoints
- Backend before frontend for each feature
- Core implementation before integration

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T001 (backend deps) || T002 (frontend deps)
```

**Phase 2 (Foundational)**:
```
T009 (add_task) || T010 (list_tasks) || T011 (complete_task)
```

**Phase 7 (Polish)**:
```
T037 (loading) || T038 (errors) || T039 (validation)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test chat with AI, verify task creation
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy (MVP!)
3. Add User Story 2 → Test independently → Deploy
4. Add User Story 3 → Test independently → Deploy
5. Add User Story 4 → Test independently → Deploy
6. Polish → Final release

### Recommended Execution Order

For single developer:
```
Phase 1 → Phase 2 → Phase 3 (MVP) → Phase 4 → Phase 5 → Phase 6 → Phase 7
```

For parallel team:
```
Phase 1 → Phase 2 → [US1 || US2 || US3 || US4] → Phase 7
```

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- MCP tools MUST use ownership verification per mcp-ownership-verification skill
- Chat service MUST follow stateless-memory-management skill pattern
