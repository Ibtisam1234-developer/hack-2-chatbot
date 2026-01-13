# Research: AI Chatbot Integration

**Feature**: 002-ai-chatbot
**Date**: 2026-01-11
**Status**: Complete

## Technology Decisions

### 1. OpenAI Agents SDK

**Decision**: Use OpenAI Agents SDK (openai-agents) for AI agent logic

**Rationale**:
- Official SDK from OpenAI designed for agentic workflows
- Built-in support for tool calling with structured outputs
- Stateless Runner pattern aligns with Constitution Principle VI
- Native async/await support for Python

**Alternatives Considered**:
- LangChain: More complex, heavier dependency footprint
- Raw OpenAI API: Would require manual tool orchestration
- Anthropic Claude: Different API patterns, less tool-calling maturity

**Integration Pattern**:
```python
from openai_agents import Agent, Runner

agent = Agent(
    model="gpt-4",
    tools=[add_task, list_tasks, complete_task],
    system_prompt="You are a helpful task management assistant..."
)

runner = Runner(agent)
response = await runner.run(messages)
```

### 2. FastMCP for Tool Server

**Decision**: Use FastMCP to implement MCP tool server

**Rationale**:
- Lightweight MCP implementation for Python
- Easy integration with FastAPI via ASGI mounting
- Supports tool definition with type annotations
- Handles tool call serialization/deserialization

**Alternatives Considered**:
- Custom MCP implementation: More work, no benefit
- Direct function calls: Bypasses MCP protocol, loses audit trail

**Integration Pattern**:
```python
from fastmcp import FastMCP

mcp = FastMCP("task-tools")

@mcp.tool()
async def add_task(user_id: str, title: str) -> str:
    # Implementation
    pass

# Mount in FastAPI
app.mount("/mcp", mcp.asgi_app())
```

### 3. Message Storage Schema

**Decision**: Store tool_calls as JSON column in Message table

**Rationale**:
- Preserves full audit trail per Constitution Principle VIII
- JSON column allows flexible tool call structure
- Single table simplifies queries and maintains conversation integrity
- PostgreSQL JSONB provides efficient querying if needed

**Alternatives Considered**:
- Separate ToolCall table: Over-normalized, complicates queries
- Store in content field: Loses structure, harder to parse

**Schema Decision**:
```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    tool_calls JSONB,  -- Array of {name, arguments, result}
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4. Frontend Chat UI

**Decision**: Use OpenAI ChatKit for chat interface

**Rationale**:
- Pre-built components designed for AI chat interfaces
- Handles message rendering, input, loading states
- Consistent with OpenAI ecosystem
- Reduces frontend development time

**Alternatives Considered**:
- Custom components: More flexibility but more work
- Vercel AI SDK UI: Good but less chat-specific
- react-chat-elements: Generic, not AI-optimized

**Integration Pattern**:
```tsx
import { Chat, Message } from '@openai/chatkit';

<Chat
  messages={messages}
  onSend={handleSend}
  isLoading={isLoading}
/>
```

### 5. Conversation History Limit

**Decision**: Fetch last 10 messages for AI context

**Rationale**:
- Balances context quality with token usage
- 10 messages typically covers recent conversation thread
- Prevents token limit issues with long conversations
- Aligns with stateless-memory-management skill

**Alternatives Considered**:
- All messages: Token limit issues, expensive
- 5 messages: May lose important context
- Summarization: Complex, adds latency

### 6. Error Handling Strategy

**Decision**: Return error strings to agent, not exceptions

**Rationale**:
- Agent can communicate errors naturally to user
- Maintains conversation flow
- Aligns with mcp-ownership-verification skill pattern
- Example: "Error: Task not found or unauthorized"

**Alternatives Considered**:
- Raise exceptions: Breaks conversation, poor UX
- Silent failures: User doesn't know what happened

## Resolved Clarifications

| Item | Resolution |
|------|------------|
| AI model | GPT-4 (configurable via environment variable) |
| Message history limit | 10 messages per request |
| Conversation title generation | First 50 characters of first user message |
| Tool call timeout | 30 seconds per tool call |
| Rate limiting | Defer to Phase II (not in scope for MVP) |

## References

- OpenAI Agents SDK: https://github.com/openai/openai-agents-python
- FastMCP: https://github.com/jlowin/fastmcp
- OpenAI ChatKit: https://github.com/openai/chatkit
- Constitution v1.1.0: Principles VI, VII, VIII
