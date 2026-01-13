# backend/src/services/chat_service.py
"""
Chat Service for AI Chatbot

Owner: AI Orchestrator
Purpose: Stateless conversation management per stateless-memory-management skill
Architecture: Database-backed memory with no local session state

Constitutional Constraints:
- REQUIRED: All queries filter by user_id (Principle IV)
- REQUIRED: No local session storage (Principle VI)
- REQUIRED: Messages persisted immediately after AI response (Principle VIII)
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Todo
from src.models.conversation import Conversation
from src.models.message import Message

logger = logging.getLogger("services.chat_service")


async def get_conversation_history(
    conversation_id: int,
    user_id: str,
    session: AsyncSession,
    limit: int = 10
) -> list[dict]:
    """
    Fetch last N messages for conversation context.

    Per stateless-memory-management skill:
    - Fetches from database on every request (no caching)
    - Filters by user_id for isolation
    - Returns in chronological order for OpenAI

    Args:
        conversation_id: The conversation to fetch history for
        user_id: The authenticated user (for isolation)
        session: Database session
        limit: Maximum messages to fetch (default 10)

    Returns:
        List of message dicts formatted for OpenAI: [{"role": "...", "content": "..."}]
    """
    statement = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.user_id == user_id  # REQUIRED: User isolation
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )

    result = await session.execute(statement)
    messages = result.scalars().all()

    # Reverse to chronological order and format for OpenAI
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(messages)
    ]

    logger.debug(f"Fetched {len(history)} messages for conversation {conversation_id}")
    return history


async def save_chat_exchange(
    conversation_id: int,
    user_id: str,
    user_message: str,
    assistant_response: str,
    tool_calls: Optional[list],
    session: AsyncSession
) -> tuple[Message, Message]:
    """
    Persist user message and AI response to database.

    Per stateless-memory-management skill:
    - MUST be called immediately after AI responds
    - Saves both user and assistant messages
    - Updates conversation timestamp
    - Stores tool_calls for audit trail (Principle VIII)

    Args:
        conversation_id: The conversation ID
        user_id: The authenticated user's ID
        user_message: The user's input message
        assistant_response: The AI's response text
        tool_calls: List of tool calls made by AI (for audit)
        session: Database session

    Returns:
        Tuple of (user_message, assistant_message) Message objects
    """
    now = datetime.utcnow()

    # Save user message
    user_msg = Message(
        conversation_id=conversation_id,
        user_id=user_id,
        role="user",
        content=user_message,
        created_at=now
    )
    session.add(user_msg)

    # Save assistant response with tool calls for audit
    assistant_msg = Message(
        conversation_id=conversation_id,
        user_id=user_id,
        role="assistant",
        content=assistant_response,
        tool_calls=tool_calls,
        created_at=now
    )
    session.add(assistant_msg)

    # Update conversation timestamp
    conversation = await session.get(Conversation, conversation_id)
    if conversation:
        conversation.updated_at = now

    await session.commit()

    logger.info(f"Saved chat exchange for conversation {conversation_id}")
    return user_msg, assistant_msg


async def create_conversation(
    user_id: str,
    first_message: str,
    session: AsyncSession
) -> Conversation:
    """
    Create a new conversation with auto-generated title.

    Title is generated from the first message (truncated to 50 chars).

    Args:
        user_id: The authenticated user's ID
        first_message: The first message (used for title generation)
        session: Database session

    Returns:
        The created Conversation object
    """
    # Generate title from first message (truncate to 50 chars)
    title = first_message[:50].strip()
    if len(first_message) > 50:
        title = title + "..."

    conversation = Conversation(
        user_id=user_id,
        title=title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)

    logger.info(f"Created conversation {conversation.id} for user {user_id}")
    return conversation


async def get_conversation_by_id(
    conversation_id: int,
    user_id: str,
    session: AsyncSession
) -> Optional[Conversation]:
    """
    Get a conversation by ID with user ownership verification.

    Args:
        conversation_id: The conversation ID
        user_id: The authenticated user's ID (for ownership check)
        session: Database session

    Returns:
        Conversation if found and owned by user, None otherwise
    """
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id  # REQUIRED: User isolation
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_conversations(
    user_id: str,
    session: AsyncSession,
    limit: int = 20
) -> list[Conversation]:
    """
    Get all conversations for a user, ordered by most recent.

    Args:
        user_id: The authenticated user's ID
        session: Database session
        limit: Maximum conversations to return

    Returns:
        List of Conversation objects
    """
    statement = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def delete_conversation(
    conversation_id: int,
    user_id: str,
    session: AsyncSession
) -> bool:
    """
    Delete a conversation and all its messages.

    Args:
        conversation_id: The conversation ID to delete
        user_id: The authenticated user's ID (for ownership check)
        session: Database session

    Returns:
        True if deleted, False if not found or unauthorized
    """
    # First verify ownership
    conversation = await get_conversation_by_id(conversation_id, user_id, session)
    if not conversation:
        return False

    # Delete all messages in the conversation
    from sqlalchemy import delete
    await session.execute(
        delete(Message).where(
            Message.conversation_id == conversation_id,
            Message.user_id == user_id
        )
    )

    # Delete the conversation
    await session.delete(conversation)
    await session.commit()

    logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
    return True
