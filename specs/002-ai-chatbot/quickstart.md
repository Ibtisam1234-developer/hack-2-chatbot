# Quickstart: AI Chatbot Integration

**Feature**: 002-ai-chatbot
**Date**: 2026-01-11
**Time to Setup**: ~10 minutes

## Prerequisites

- Node.js 20+
- Python 3.11+
- Existing TodoWeb application running (Phase I/II complete)
- OpenRouter API key (free at https://openrouter.ai/keys)

## Step 1: Install Backend Dependencies

```bash
cd backend
pip install openai-agents litellm fastmcp
```

Add to `requirements.txt`:
```
openai-agents>=0.0.5
litellm>=1.0.0
fastmcp>=0.1.0
```

## Step 2: Install Frontend Dependencies

```bash
npm install @openai/chatkit
```

## Step 3: Configure Environment

Add to `backend/.env`:
```env
# Get your free API key at https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key

# Free tier models via LiteLLM (use openrouter/ prefix):
# - openrouter/google/gemma-2-9b-it:free (recommended)
# - openrouter/meta-llama/llama-3.2-3b-instruct:free
# - openrouter/qwen/qwen-2-7b-instruct:free
OPENROUTER_MODEL=openrouter/google/gemma-2-9b-it:free
```

## Step 4: Run Database Migration

```bash
cd backend
python -c "
from src.db.database import engine
from src.models.conversation import Conversation
from src.models.message import Message
from sqlmodel import SQLModel
import asyncio

async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print('Migration complete!')

asyncio.run(migrate())
"
```

Or run the SQL directly:
```sql
-- Run in Neon console or psql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);

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
CREATE INDEX idx_messages_user_id ON messages(user_id);
```

## Step 5: Start the Application

Terminal 1 - Backend:
```bash
cd backend
python run_dev.py
```

Terminal 2 - Frontend:
```bash
npm run dev
```

## Step 6: Test the Chat Endpoint

```bash
# Get a valid JWT token (login first via frontend)
TOKEN="your-jwt-token"

# Send a chat message
curl -X POST http://localhost:8000/api/user123/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Add a task to buy groceries"}'
```

Expected response:
```json
{
  "conversation_id": 1,
  "response": "I've added 'Buy groceries' to your task list.",
  "tool_calls": [
    {
      "name": "add_task",
      "arguments": {"user_id": "user123", "title": "Buy groceries"},
      "result": "Task 'Buy groceries' added with ID 1."
    }
  ]
}
```

## Step 7: Access the Chat UI

1. Open http://localhost:3000
2. Log in with your account
3. Navigate to the Chat page
4. Start chatting with the AI assistant

## Verification Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Database tables created (conversations, messages)
- [ ] Chat endpoint returns 200 with valid JWT
- [ ] AI creates tasks via natural language
- [ ] Tasks appear in the todo list
- [ ] Conversation history persists across page reloads

## Troubleshooting

### "OPENROUTER_API_KEY not set"
- Verify `OPENROUTER_API_KEY` is in `backend/.env`
- Restart the backend server

### "401 Unauthorized"
- Verify JWT token is valid and not expired
- Check `BETTER_AUTH_SECRET` matches in both `.env` files

### "Conversation not found"
- Verify `conversation_id` exists and belongs to the user
- Check database connection

### "Tool call failed"
- Check backend logs for detailed error
- Verify Task table exists and is accessible
- Some free models have limited function calling - try `google/gemma-2-9b-it:free`

## Next Steps

After verifying the quickstart:
1. Run `/sp.tasks` to generate implementation tasks
2. Implement each component following the plan
3. Run tests to verify functionality
