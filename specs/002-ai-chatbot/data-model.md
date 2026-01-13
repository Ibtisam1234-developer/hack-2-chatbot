# Data Model: AI Chatbot Integration

**Feature**: 002-ai-chatbot
**Date**: 2026-01-11
**Status**: Complete

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│      User       │       │  Conversation   │       │     Message     │
│  (Better Auth)  │       │                 │       │                 │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──1:N──│ id (PK)         │──1:N──│ id (PK)         │
│ email           │       │ user_id (FK)    │       │ conversation_id │
│ ...             │       │ title           │       │ user_id (FK)    │
└─────────────────┘       │ created_at      │       │ role            │
                          │ updated_at      │       │ content         │
                          └─────────────────┘       │ tool_calls      │
                                                    │ created_at      │
┌─────────────────┐                                 └─────────────────┘
│      Task       │
│   (Existing)    │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │
│ title           │
│ description     │
│ is_completed    │
│ ...             │
└─────────────────┘
```

## Entities

### Conversation

Represents a chat thread between a user and the AI assistant.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTO_INCREMENT | Unique conversation identifier |
| user_id | VARCHAR(255) | NOT NULL, INDEX | Owner of the conversation (from JWT sub) |
| title | VARCHAR(100) | NOT NULL | Display title (auto-generated from first message) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | When conversation started |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last message timestamp |

**Indexes**:
- `idx_conversations_user_id` on `user_id` (for listing user's conversations)
- `idx_conversations_user_updated` on `(user_id, updated_at DESC)` (for sorted listing)

**SQLModel Definition**:
```python
# backend/src/models/conversation.py
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, nullable=False)
    title: str = Field(max_length=100, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Message

Represents a single message within a conversation.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTO_INCREMENT | Unique message identifier |
| conversation_id | INTEGER | FK → conversations.id, NOT NULL | Parent conversation |
| user_id | VARCHAR(255) | NOT NULL, INDEX | Message owner (for isolation) |
| role | VARCHAR(20) | NOT NULL | "user" or "assistant" |
| content | TEXT | NOT NULL | Message text content |
| tool_calls | JSONB | NULLABLE | Array of tool call records |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | When message was created |

**Indexes**:
- `idx_messages_conversation_id` on `conversation_id` (for fetching conversation messages)
- `idx_messages_conv_created` on `(conversation_id, created_at DESC)` (for ordered history)
- `idx_messages_user_id` on `user_id` (for user isolation queries)

**SQLModel Definition**:
```python
# backend/src/models/message.py
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from datetime import datetime
from typing import Optional, List, Any

class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True, nullable=False)
    user_id: str = Field(index=True, nullable=False)
    role: str = Field(max_length=20, nullable=False)  # "user" or "assistant"
    content: str = Field(nullable=False)
    tool_calls: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
```

## Tool Call Schema

The `tool_calls` JSON column stores an array of tool invocations:

```json
[
  {
    "name": "add_task",
    "arguments": {
      "user_id": "user_123",
      "title": "Buy groceries",
      "description": null
    },
    "result": "Task 'Buy groceries' added with ID 42."
  },
  {
    "name": "list_tasks",
    "arguments": {
      "user_id": "user_123",
      "status": "pending"
    },
    "result": "Your tasks:\n- [42] ○ Buy groceries\n- [41] ○ Finish report"
  }
]
```

## Validation Rules

### Conversation
- `user_id`: Required, must match JWT `sub` claim
- `title`: Required, max 100 characters, auto-generated if not provided

### Message
- `conversation_id`: Required, must reference existing conversation owned by user
- `user_id`: Required, must match conversation owner
- `role`: Required, must be "user" or "assistant"
- `content`: Required, non-empty string

## State Transitions

### Conversation Lifecycle
```
[New Message without conversation_id]
    │
    ▼
┌─────────────────┐
│    CREATED      │ ← Auto-generate title from first message
└────────┬────────┘
         │
         ▼ [Each new message]
┌─────────────────┐
│    ACTIVE       │ ← Update updated_at timestamp
└────────┬────────┘
         │
         ▼ [User deletes - future feature]
┌─────────────────┐
│    DELETED      │
└─────────────────┘
```

### Message Lifecycle
```
[User sends message]
    │
    ▼
┌─────────────────┐
│  USER MESSAGE   │ ← role="user", no tool_calls
│    CREATED      │
└────────┬────────┘
         │
         ▼ [AI processes]
┌─────────────────┐
│ ASSISTANT MSG   │ ← role="assistant", tool_calls populated
│    CREATED      │
└─────────────────┘
```

## Migration SQL

```sql
-- Create conversations table
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_user_updated ON conversations(user_id, updated_at DESC);

-- Create messages table
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_conv_created ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_messages_user_id ON messages(user_id);
```

## Relationships to Existing Entities

### Task (Existing)
- No direct foreign key relationship to Conversation/Message
- Tasks are accessed via MCP tools using `user_id`
- Tool calls reference task IDs in their arguments/results

### User (Better Auth)
- `user_id` in Conversation and Message references Better Auth user
- No explicit foreign key (Better Auth manages user table)
- User isolation enforced at application layer via JWT `sub` claim
