# backend/src/api/routes/chat.py
"""
Chat API Routes for AI Chatbot

Owner: Backend API Engineer
Purpose: RESTful endpoints for AI chat operations with user isolation
Architecture: FastAPI async routes with stateless memory management

Constitutional Constraints:
- REQUIRED: All routes MUST use Depends(get_current_user_id) for authentication
- REQUIRED: All database queries MUST filter by user_id
- REQUIRED: Stateless processing - no local session storage (Principle VI)
- REQUIRED: All tool calls logged for audit trail (Principle VIII)
"""

import json
import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db import get_session
from src.db.connection import get_session_factory
from src.api.middleware.auth import get_current_user_id
from src.api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ToolCallSchema,
    ConversationSchema,
    ConversationWithMessagesSchema,
    MessageSchema
)
from src.services.chat_service import (
    get_conversation_history,
    save_chat_exchange,
    create_conversation,
    get_conversation_by_id,
    get_user_conversations,
    delete_conversation
)
from src.services.agent_service import get_agent_service
from src.mcp.tools.task_tools import add_task_impl, list_tasks_impl, complete_task_impl, update_task_impl, delete_task_impl
from src.models.message import Message

# Configure logging
logger = logging.getLogger("api.chat")

# Create router
router = APIRouter(
    prefix="/api",
    tags=["chat"],
    responses={
        401: {"description": "Authentication failed - invalid or missing JWT token"},
        500: {"description": "Internal server error"}
    }
)


async def execute_tool(tool_name: str, tool_args: str, user_id: str) -> str:
    """
    Execute an MCP tool with user_id injection.

    Per Constitution Principle VII: Tools are the ONLY way AI accesses data.
    The user_id is injected from JWT, never from AI arguments.

    Args:
        tool_name: Name of the tool to execute
        tool_args: JSON string of tool arguments
        user_id: Authenticated user's ID from JWT

    Returns:
        Tool result as string
    """
    try:
        args = json.loads(tool_args)
    except json.JSONDecodeError:
        args = {}

    logger.info(f"Executing tool {tool_name} for user {user_id}")

    # Validate task_id for tools that require it
    tools_requiring_id = {"complete_task", "update_task", "delete_task"}
    if tool_name in tools_requiring_id:
        task_id = args.get("task_id", "")
        if not task_id or not str(task_id).strip():
            return "Error: Task ID is required. Please use 'show my tasks' to see your tasks with their IDs, then specify which task to modify."

    if tool_name == "add_task":
        return await add_task_impl(
            user_id=user_id,
            title=args.get("title", ""),
            description=args.get("description")
        )
    elif tool_name == "list_tasks":
        return await list_tasks_impl(
            user_id=user_id,
            status=args.get("status", "all")
        )
    elif tool_name == "complete_task":
        return await complete_task_impl(
            user_id=user_id,
            task_id=args.get("task_id", "")
        )
    elif tool_name == "update_task":
        return await update_task_impl(
            user_id=user_id,
            task_id=args.get("task_id", ""),
            title=args.get("title"),
            description=args.get("description")
        )
    elif tool_name == "delete_task":
        return await delete_task_impl(
            user_id=user_id,
            task_id=args.get("task_id", "")
        )
    else:
        return f"Error: Unknown tool '{tool_name}'"


@router.post(
    "/{user_id}/chat",
    response_model=ChatResponse,
    summary="Send a chat message to the AI assistant",
    description="Processes a user message through the AI agent, which may invoke MCP tools to manage tasks.",
    responses={
        200: {"description": "Successful response from AI"},
        400: {"description": "Invalid request (empty message)"},
        403: {"description": "User ID mismatch with JWT"},
        404: {"description": "Conversation not found or unauthorized"}
    }
)
async def chat(
    user_id: str,
    request: ChatRequest,
    auth_user_id: Annotated[str, Depends(get_current_user_id)]
) -> ChatResponse:
    """
    Stateless chat endpoint per stateless-memory-management skill.

    Flow:
    1. Validates user matches JWT
    2. Gets or creates conversation
    3. Fetches history from DB (stateless)
    4. Processes with AI agent
    5. Persists exchange to DB
    6. Returns response

    Args:
        user_id: User ID from path (must match JWT)
        request: Chat request with message and optional conversation_id
        auth_user_id: User ID from JWT token

    Returns:
        ChatResponse with conversation_id, response text, and tool calls
    """
    # Verify user matches JWT (security check)
    if user_id != auth_user_id:
        logger.warning(f"User mismatch: path={user_id}, jwt={auth_user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID mismatch with authentication token"
        )

    try:
        session_factory = get_session_factory()
        logger.info(f"Got session factory for user {user_id}")

        # Get or create conversation
        conversation_id = request.conversation_id

        if conversation_id:
            # Verify conversation exists and belongs to user
            async with session_factory() as session:
                conversation = await get_conversation_by_id(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    session=session
                )
                if not conversation:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Conversation not found"
                    )
            logger.info(f"Found existing conversation {conversation_id}")
        else:
            # Create new conversation
            async with session_factory() as session:
                conversation = await create_conversation(
                    user_id=user_id,
                    first_message=request.message,
                    session=session
                )
                conversation_id = conversation.id
            logger.info(f"Created new conversation {conversation_id}")

        # Step 1: Fetch history from DB (stateless - no local cache)
        async with session_factory() as session:
            history = await get_conversation_history(
                conversation_id=conversation_id,
                user_id=user_id,
                session=session,
                limit=10
            )
        logger.info(f"Fetched {len(history)} messages from history")

        # Step 2-3: Process with AI agent
        logger.info("Getting agent service...")
        agent = get_agent_service()
        logger.info(f"Processing message with agent model: {agent.model}")
        result = await agent.process_message(
            user_message=request.message,
            conversation_history=history,
            user_id=user_id,
            tool_executor=execute_tool
        )
        logger.info(f"Agent returned response with {len(result.get('tool_calls') or [])} tool calls")

        # Step 4: Persist to DB (stateless - no local storage)
        async with session_factory() as session:
            await save_chat_exchange(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=request.message,
                assistant_response=result["response"],
                tool_calls=result["tool_calls"],
                session=session
            )

        # Format tool calls for response
        tool_calls_response = None
        if result["tool_calls"]:
            tool_calls_response = [
                ToolCallSchema(
                    tool=tc["tool"],
                    arguments=tc["arguments"],
                    result=tc["result"]
                )
                for tc in result["tool_calls"]
            ]

        logger.info(f"Chat processed for user {user_id}, conversation {conversation_id}")

        return ChatResponse(
            conversation_id=conversation_id,
            response=result["response"],
            tool_calls=tool_calls_response
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Chat processing error for user {user_id}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@router.get(
    "/{user_id}/conversations",
    response_model=list[ConversationSchema],
    summary="List user's conversations",
    description="Returns all conversations for the authenticated user, sorted by most recent first.",
    responses={
        200: {"description": "List of conversations"},
        403: {"description": "User ID mismatch with JWT"}
    }
)
async def list_conversations(
    user_id: str,
    auth_user_id: Annotated[str, Depends(get_current_user_id)]
) -> list[ConversationSchema]:
    """
    List all conversations for the authenticated user.

    Args:
        user_id: User ID from path (must match JWT)
        auth_user_id: User ID from JWT token

    Returns:
        List of ConversationSchema objects
    """
    if user_id != auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID mismatch with authentication token"
        )

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            conversations = await get_user_conversations(
                user_id=user_id,
                session=session
            )
            return [ConversationSchema.model_validate(c) for c in conversations]

    except Exception as e:
        logger.error(f"Failed to list conversations for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get(
    "/{user_id}/conversations/{conversation_id}",
    response_model=ConversationWithMessagesSchema,
    summary="Get conversation with messages",
    description="Returns a conversation and its full message history.",
    responses={
        200: {"description": "Conversation with messages"},
        403: {"description": "User ID mismatch with JWT"},
        404: {"description": "Conversation not found or unauthorized"}
    }
)
async def get_conversation(
    user_id: str,
    conversation_id: int,
    auth_user_id: Annotated[str, Depends(get_current_user_id)]
) -> ConversationWithMessagesSchema:
    """
    Get a conversation with its full message history.

    Args:
        user_id: User ID from path (must match JWT)
        conversation_id: Conversation ID
        auth_user_id: User ID from JWT token

    Returns:
        ConversationWithMessagesSchema with messages
    """
    if user_id != auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID mismatch with authentication token"
        )

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            conversation = await get_conversation_by_id(
                conversation_id=conversation_id,
                user_id=user_id,
                session=session
            )

            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )

            # Get all messages
            statement = (
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.user_id == user_id
                )
                .order_by(Message.created_at.asc())
            )
            result = await session.execute(statement)
            messages = result.scalars().all()

            return ConversationWithMessagesSchema(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                messages=[MessageSchema.model_validate(m) for m in messages]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation {conversation_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )


@router.delete(
    "/{user_id}/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    description="Deletes a conversation and all its messages.",
    responses={
        204: {"description": "Conversation deleted successfully"},
        403: {"description": "User ID mismatch with JWT"},
        404: {"description": "Conversation not found or unauthorized"}
    }
)
async def delete_conversation_endpoint(
    user_id: str,
    conversation_id: int,
    auth_user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Delete a conversation and all its messages.

    Args:
        user_id: User ID from path (must match JWT)
        conversation_id: Conversation ID to delete
        auth_user_id: User ID from JWT token

    Returns:
        204 No Content on success
    """
    if user_id != auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User ID mismatch with authentication token"
        )

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            deleted = await delete_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                session=session
            )

            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation {conversation_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )
