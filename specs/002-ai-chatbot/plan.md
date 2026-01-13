# Implementation Plan: AI Chatbot Integration

**Branch**: `002-ai-chatbot` | **Date**: 2026-01-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-ai-chatbot/spec.md`

## Summary

Implement an AI-powered chatbot that enables users to manage their tasks through natural language conversation. The system uses OpenAI Agents SDK with MCP tools for task operations, persists all conversations in Neon PostgreSQL, and maintains complete statelessness for horizontal scalability.

**Key Components**:
1. **Database Layer**: Conversation and Message tables with user isolation
2. **MCP Tool Server**: Task management tools (add, list, complete) with ownership verification
3. **AI Agent**: OpenAI Agents SDK Runner with stateless memory management
4. **Frontend**: Chat UI integrated with OpenAI ChatKit

## Technical Context

**Language/Version**: Python 3.11+ (Backend), TypeScript 5+ (Frontend)
**Primary Dependencies**: FastAPI, OpenAI Agents SDK, FastMCP, Next.js 16, React 19, OpenAI ChatKit
**Storage**: Neon PostgreSQL (asyncpg driver), SQLModel ORM
**Testing**: pytest (backend), Jest/Vitest (frontend)
**Target Platform**: Web application (Linux server deployment)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: <10s task creation, <5s task listing, <2s history load (per SC-001/002/008)
**Constraints**: Stateless architecture, user isolation, audit trail for all AI actions
**Scale/Scope**: Multi-tenant SaaS, 100+ messages per conversation supported

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Implementation |
|-----------|--------|----------------|
| I. Multi-Agent Collaboration | ✅ PASS | Four specialized agents: @db-specialist, @mcp-engineer, @ai-orchestrator, @frontend-dev |
| II. Authentication & Authorization | ✅ PASS | Reuse existing Better Auth JWT; extract user_id from `sub` claim |
| III. Service Layer Transformation | ✅ PASS | MCP tools wrap existing task service functions |
| IV. Security: User Isolation | ✅ PASS | All queries filter by user_id; MCP tools use ownership verification |
| V. Async Python Development | ✅ PASS | All handlers async; asyncpg for database |
| VI. Stateless Architecture | ✅ PASS | No local session; history fetched from DB per request |
| VII. Tool-Only AI Access (MCP) | ✅ PASS | AI uses MCP tools exclusively; no direct DB access |
| VIII. AI Audit Trail | ✅ PASS | All messages and tool calls logged to Message table |

**Gate Result**: PASS - All principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/002-ai-chatbot/
├── plan.md              # This file
├── research.md          # Phase 0: Technology decisions
├── data-model.md        # Phase 1: Conversation/Message schemas
├── quickstart.md        # Phase 1: Developer setup guide
├── contracts/           # Phase 1: API contracts
│   ├── chat-api.yaml    # OpenAPI spec for chat endpoint
│   └── mcp-tools.md     # MCP tool definitions
└── tasks.md             # Phase 2: Implementation tasks
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── conversation.py    # Conversation SQLModel
│   │   └── message.py         # Message SQLModel
│   ├── services/
│   │   ├── chat_service.py    # Chat processing logic
│   │   └── agent_service.py   # OpenAI Runner wrapper
│   ├── mcp/
│   │   ├── server.py          # FastMCP server setup
│   │   └── tools/
│   │       └── task_tools.py  # add_task, list_tasks, complete_task
│   └── api/
│       └── routes/
│           └── chat.py        # POST /api/{user_id}/chat
└── tests/
    ├── test_chat.py           # Chat endpoint tests
    ├── test_mcp_tools.py      # MCP tool tests
    └── test_user_isolation.py # Security tests

app/                           # Next.js app directory
├── chat/
│   └── page.tsx               # Chat page with ChatKit
└── api/
    └── chat/
        └── route.ts           # API route proxy (optional)

components/
├── ChatInterface.tsx          # Main chat component
├── ConversationList.tsx       # Sidebar conversation list
└── MessageBubble.tsx          # Individual message display

lib/
└── chat-client.ts             # Chat API client
```

**Structure Decision**: Web application structure with existing backend/ and app/ directories. New MCP server mounted within FastAPI application.

## Agent Assignments

| Agent | Responsibility | Deliverables |
|-------|---------------|--------------|
| @db-specialist | Database schema and migrations | Conversation/Message models, migration scripts |
| @mcp-engineer | MCP tool server | FastMCP server, task tools with ownership verification |
| @ai-orchestrator | AI agent logic | OpenAI Runner integration, stateless memory management |
| @frontend-dev | Chat UI | ChatKit integration, conversation list, message display |

## Complexity Tracking

No constitution violations requiring justification.

## Dependencies

### External Packages (Backend)

| Package | Version | Purpose |
|---------|---------|---------|
| openai-agents | ^0.1.0 | OpenAI Agents SDK for AI logic |
| fastmcp | ^0.1.0 | MCP server framework |
| sqlmodel | ^0.0.14 | Async ORM for Conversation/Message |

### External Packages (Frontend)

| Package | Version | Purpose |
|---------|---------|---------|
| @openai/chatkit | ^0.1.0 | Pre-built chat UI components |

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OpenAI API latency | Medium | High | Set timeout, show loading state, consider streaming |
| Prompt injection attacks | Low | High | MCP tools enforce user isolation; no direct DB access |
| Message history too large | Low | Medium | Limit to last 10 messages; paginate history view |
| Tool call failures | Medium | Medium | Return error string to agent; log for debugging |

## Generated Artifacts

| Artifact | Status | Path |
|----------|--------|------|
| research.md | ✅ Complete | `specs/002-ai-chatbot/research.md` |
| data-model.md | ✅ Complete | `specs/002-ai-chatbot/data-model.md` |
| chat-api.yaml | ✅ Complete | `specs/002-ai-chatbot/contracts/chat-api.yaml` |
| mcp-tools.md | ✅ Complete | `specs/002-ai-chatbot/contracts/mcp-tools.md` |
| quickstart.md | ✅ Complete | `specs/002-ai-chatbot/quickstart.md` |

## Next Steps

Run `/sp.tasks` to generate implementation tasks based on this plan.
