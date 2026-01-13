---
name: stateless-memory-management
description: Protocol for managing conversation history in a stateless architecture using database-backed memory.
---

# Stateless Memory Management Protocol

## Overview

This skill defines the protocol for handling conversation memory in a stateless server architecture. All conversation history is stored in the database and fetched on-demand for each request, ensuring horizontal scalability per Constitution Principle VI (Stateless Architecture).

## Core Principle

**CRITICAL**: The server stores NO local session state. All conversation context is fetched from the database at request time and persisted immediately after the AI responds.

## Request Cycle

### Step 1: Fetch Conversation History

**MUST**: Query the Message table for recent messages when handling a chat request.

```python
# backend/src/services/chat_service.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.message import Message

async def get_conversation_history(
    conversation_id: int,
    user_id: str,
    session: AsyncSession,
    limit: int = 10
) -> list[dict]:
    """
    Fetch last N messages for conversation context

    Args:
        conversation_id: The conversation to fetch history for
        user_id: The authenticated user (for isolation)
        session: Database session
        limit: Maximum messages to fetch (default 10)

    Returns:
        List of message dicts formatted for OpenAI
    """
    statement = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.user_id == user_id  # ✅ REQUIRED: User isolation
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )

    result = await session.execute(statement)
    messages = result.scalars().all()

    # Reverse to chronological order and format for OpenAI
    return [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(messages)
    ]
```

### Step 2: Format Messages for OpenAI Runner

**MUST**: Format conversation history as an array of role/content objects.

```python
# Message format for OpenAI Agents SDK
messages = [
    {"role": "user", "content": "Add a task to buy groceries"},
    {"role": "assistant", "content": "I've added 'Buy groceries' to your task list."},
    {"role": "user", "content": "What tasks do I have?"},
    # ... current message appended
]
```

**Format Rules**:
- `role`: Must be "user" or "assistant"
- `content`: The message text (string)
- Order: Chronological (oldest first)
- Limit: Last 10 messages (configurable)

### Step 3: Pass to OpenAI Runner

**MUST**: Include conversation history when invoking the AI agent.

```python
# backend/src/services/agent_service.py
from openai_agents import Runner

async def process_chat_message(
    user_message: str,
    conversation_history: list[dict],
    user_id: str,
    tools: list
) -> dict:
    """
    Process user message with conversation context

    Args:
        user_message: The new message from user
        conversation_history: Previous messages from database
        user_id: For tool authorization
        tools: MCP tools available to agent

    Returns:
        Agent response with tool calls
    """
    # Append current user message to history
    messages = conversation_history + [
        {"role": "user", "content": user_message}
    ]

    # Create runner with stateless configuration
    runner = Runner(
        model="gpt-4",
        tools=tools,
        messages=messages  # ✅ Pass full context
    )

    # Execute agent (stateless - no session stored)
    response = await runner.run()

    return {
        "response": response.content,
        "tool_calls": response.tool_calls
    }
```

### Step 4: Persist New Messages

**MUST**: Write both user message and AI response to database immediately after processing.

```python
# backend/src/services/chat_service.py
from datetime import datetime
from models.message import Message
from models.conversation import Conversation

async def save_chat_exchange(
    conversation_id: int,
    user_id: str,
    user_message: str,
    assistant_response: str,
    tool_calls: list,
    session: AsyncSession
) -> None:
    """
    Persist user message and AI response to database

    MUST be called immediately after AI responds
    """
    now = datetime.utcnow()

    # Save user message
    user_msg = Message(
        conversation_id=conversation_id,
        user_id=user_id,  # ✅ REQUIRED: User isolation
        role="user",
        content=user_message,
        created_at=now
    )
    session.add(user_msg)

    # Save assistant response
    assistant_msg = Message(
        conversation_id=conversation_id,
        user_id=user_id,  # ✅ REQUIRED: User isolation
        role="assistant",
        content=assistant_response,
        tool_calls=tool_calls,  # Store tool calls for audit
        created_at=now
    )
    session.add(assistant_msg)

    # Update conversation timestamp
    conversation = await session.get(Conversation, conversation_id)
    if conversation:
        conversation.updated_at = now

    await session.commit()
```

## Complete Request Handler

**MUST**: Follow this pattern for all chat endpoints.

```python
# backend/src/api/routes/chat.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/{user_id}/chat")
async def chat(
    user_id: str,
    request: ChatRequest,
    auth_user_id: Annotated[str, Depends(get_current_user_id)],
    session: AsyncSession = Depends(get_session)
):
    """
    Stateless chat endpoint

    1. Validates user
    2. Fetches history from DB
    3. Processes with AI
    4. Persists exchange to DB
    5. Returns response
    """
    # Verify user matches JWT
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="User mismatch")

    # Get or create conversation
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation_id = await create_conversation(user_id, session)

    # Step 1: Fetch history (stateless - from DB)
    history = await get_conversation_history(
        conversation_id=conversation_id,
        user_id=user_id,
        session=session,
        limit=10
    )

    # Step 2-3: Process with AI
    result = await process_chat_message(
        user_message=request.message,
        conversation_history=history,
        user_id=user_id,
        tools=get_mcp_tools(user_id)
    )

    # Step 4: Persist to DB (stateless - no local storage)
    await save_chat_exchange(
        conversation_id=conversation_id,
        user_id=user_id,
        user_message=request.message,
        assistant_response=result["response"],
        tool_calls=result["tool_calls"],
        session=session
    )

    return {
        "conversation_id": conversation_id,
        "response": result["response"],
        "tool_calls": result["tool_calls"]
    }
```

## Database Schema

**MUST**: Message table includes all required fields for stateless retrieval.

```python
# backend/src/models/message.py
from sqlmodel import SQLModel, Field, Column, JSON
from datetime import datetime
from typing import Optional

class Message(SQLModel, table=True):
    """Message model for conversation history"""
    __tablename__ = "messages"

    id: int = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    user_id: str = Field(index=True, nullable=False)  # ✅ User isolation
    role: str = Field(max_length=20)  # "user" or "assistant"
    content: str = Field()
    tool_calls: Optional[list] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
```

## Stateless Guarantees

### What MUST NOT be stored locally:
- Session data
- Conversation state
- User preferences cache
- Message history cache

### What MUST be stored in database:
- All messages (user and assistant)
- Conversation metadata
- Tool call audit logs
- User preferences

## Performance Optimization

### Query Optimization

```python
# Use composite index for efficient history queries
# SQL: CREATE INDEX idx_messages_conv_created ON messages(conversation_id, created_at DESC);

statement = (
    select(Message)
    .where(Message.conversation_id == conversation_id)
    .order_by(Message.created_at.desc())
    .limit(10)
)
```

### Connection Pooling

Leverage Neon's connection pooling (see neon-tenant-isolation skill) to handle concurrent stateless requests efficiently.

## Security Checklist

- [ ] All message queries filter by user_id
- [ ] Conversation ownership verified before access
- [ ] No local session storage
- [ ] Messages persisted immediately after AI response
- [ ] Tool calls logged for audit trail
- [ ] History limit prevents memory exhaustion

## Testing

```python
# backend/tests/test_stateless_memory.py
import pytest

@pytest.mark.asyncio
async def test_history_fetched_from_database(client, db_session):
    """Verify history is fetched from DB, not local cache"""
    # Create conversation with messages in DB
    conv_id = await create_test_conversation(db_session)
    await create_test_messages(conv_id, count=5, db_session=db_session)

    # Send new message
    response = await client.post(f"/api/user123/chat", json={
        "message": "What did we discuss?",
        "conversation_id": conv_id
    })

    # Verify AI received history context
    assert response.status_code == 200
    # AI should reference previous messages

@pytest.mark.asyncio
async def test_messages_persisted_after_response(client, db_session):
    """Verify both user and assistant messages are saved"""
    response = await client.post("/api/user123/chat", json={
        "message": "Add a task"
    })

    conv_id = response.json()["conversation_id"]

    # Query DB directly
    messages = await get_all_messages(conv_id, db_session)

    assert len(messages) == 2  # User + Assistant
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
```

## References

- Constitution Principle VI: Stateless Architecture
- Constitution Principle VIII: AI Audit Trail
- OpenAI Agents SDK: https://github.com/openai/openai-agents-python
