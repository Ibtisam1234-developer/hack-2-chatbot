"""
Todo API Routes for FastAPI

Owner: Backend API Engineer
Purpose: RESTful endpoints for todo CRUD operations with user isolation
Architecture: FastAPI async routes with SQLModel and JWT authentication

Constitutional Constraints:
- REQUIRED: All routes MUST use Depends(get_current_user_id) for authentication
- REQUIRED: All database queries MUST filter by user_id
- REQUIRED: Return 404 (not 403) when todo doesn't belong to user (prevent info leakage)
- REQUIRED: Async/await for all database operations
- REQUIRED: Proper HTTP status codes (201 for create, 204 for delete, etc.)

Security Protocol:
1. Extract user_id from JWT via get_current_user_id dependency
2. Filter all queries by user_id (never trust client input)
3. Return 404 if todo not found OR doesn't belong to user
4. Never expose existence of other users' todos

All endpoints enforce strict user isolation per constitution Principle IV.
"""

import logging
from typing import Annotated, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlmodel import col

from src.db import (
    get_session,
    Todo,
    TodoCreate,
    TodoUpdate,
    TodoResponse
)
from src.api.middleware.auth import get_current_user_id

# Configure logging
logger = logging.getLogger("api.todos")

# Create router with prefix and tags
router = APIRouter(
    prefix="/api/todos",
    tags=["todos"],
    responses={
        401: {"description": "Authentication failed - invalid or missing JWT token"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new todo",
    description="Creates a new todo item for the authenticated user. The user_id is automatically extracted from the JWT token.",
    responses={
        201: {"description": "Todo created successfully"},
        400: {"description": "Invalid request format"},
        422: {"description": "Validation error"}
    }
)
async def create_todo(
    todo_data: TodoCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> TodoResponse:
    """
    Create a new todo for the authenticated user.

    Security:
    - user_id is extracted from JWT (never from request body)
    - Todo is automatically associated with authenticated user

    Args:
        todo_data: Todo creation data (title, description, is_completed)
        user_id: Automatically extracted from JWT token
        session: Database session

    Returns:
        TodoResponse: Created todo with all fields including id and timestamps
    """
    try:
        # Debug: Log incoming request data
        logger.info(f"Creating todo with data: title={todo_data.title}, category={todo_data.category}, due_date={todo_data.due_date}")

        # Convert timezone-aware datetime to timezone-naive for PostgreSQL compatibility
        due_date_naive = None
        if todo_data.due_date:
            if todo_data.due_date.tzinfo is not None:
                # Remove timezone info to match created_at/updated_at
                due_date_naive = todo_data.due_date.replace(tzinfo=None)
            else:
                due_date_naive = todo_data.due_date

        # Create new todo with user_id from JWT
        new_todo = Todo(
            user_id=user_id,
            title=todo_data.title,
            description=todo_data.description,
            category=todo_data.category,
            due_date=due_date_naive,
            is_completed=todo_data.is_completed,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        session.add(new_todo)
        await session.commit()
        await session.refresh(new_todo)

        logger.info(f"Todo created: {new_todo.id} (category={new_todo.category}) for user: {user_id}")
        return TodoResponse.model_validate(new_todo)

    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to create todo for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create todo"
        )


@router.get(
    "",
    response_model=List[TodoResponse],
    summary="List all todos for authenticated user",
    description="Retrieves all todo items belonging to the authenticated user, ordered by creation date (newest first)",
    responses={
        200: {"description": "Successfully retrieved todo list"}
    }
)
async def list_todos(
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> List[TodoResponse]:
    """
    List all todos for the authenticated user.

    Security:
    - Only returns todos where user_id matches JWT sub claim
    - Other users' todos are never visible

    Args:
        user_id: Automatically extracted from JWT token
        session: Database session

    Returns:
        List[TodoResponse]: List of todos ordered by created_at (newest first)
    """
    try:
        # Query todos filtered by user_id (CRITICAL: user isolation)
        statement = (
            select(Todo)
            .where(col(Todo.user_id) == user_id)
            .order_by(Todo.created_at.desc())
        )

        result = await session.execute(statement)
        todos = result.scalars().all()

        logger.debug(f"Retrieved {len(todos)} todos for user: {user_id}")
        return [TodoResponse.model_validate(todo) for todo in todos]

    except Exception as e:
        logger.error(f"Failed to list todos for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve todos"
        )


@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Get a specific todo",
    description="Retrieves a single todo by ID. Returns 404 if todo doesn't exist or doesn't belong to authenticated user.",
    responses={
        200: {"description": "Successfully retrieved todo"},
        404: {"description": "Todo not found or doesn't belong to user"}
    }
)
async def get_todo(
    todo_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> TodoResponse:
    """
    Get a specific todo by ID.

    Security:
    - Returns 404 if todo doesn't exist OR doesn't belong to user
    - Never reveals whether todo exists for another user (prevents info leakage)

    Args:
        todo_id: UUID of the todo to retrieve
        user_id: Automatically extracted from JWT token
        session: Database session

    Returns:
        TodoResponse: Todo with all fields

    Raises:
        HTTPException(404): If todo not found or doesn't belong to user
    """
    try:
        # Query todo with BOTH id and user_id filters (CRITICAL: user isolation)
        statement = select(Todo).where(
            col(Todo.id) == todo_id,
            col(Todo.user_id) == user_id
        )

        result = await session.execute(statement)
        todo = result.scalar_one_or_none()

        if not todo:
            # Return 404 regardless of whether todo exists for another user
            # This prevents information leakage about other users' todos
            logger.warning(f"Todo not found or access denied: {todo_id} for user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo not found"
            )

        logger.debug(f"Retrieved todo: {todo_id} for user: {user_id}")
        return TodoResponse.model_validate(todo)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get todo {todo_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve todo"
        )


@router.put(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Update a todo",
    description="Updates an existing todo. Only provided fields are updated. Returns 404 if todo doesn't exist or doesn't belong to authenticated user.",
    responses={
        200: {"description": "Todo updated successfully"},
        404: {"description": "Todo not found or doesn't belong to user"},
        422: {"description": "Validation error"}
    }
)
async def update_todo(
    todo_id: UUID,
    todo_data: TodoUpdate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> TodoResponse:
    """
    Update an existing todo.

    Security:
    - Only updates todo if it belongs to authenticated user
    - Returns 404 if todo doesn't exist or doesn't belong to user
    - user_id cannot be changed (enforced by not accepting it in request)

    Args:
        todo_id: UUID of the todo to update
        todo_data: Fields to update (all optional)
        user_id: Automatically extracted from JWT token
        session: Database session

    Returns:
        TodoResponse: Updated todo with all fields

    Raises:
        HTTPException(404): If todo not found or doesn't belong to user
    """
    try:
        # Query todo with BOTH id and user_id filters (CRITICAL: user isolation)
        statement = select(Todo).where(
            col(Todo.id) == todo_id,
            col(Todo.user_id) == user_id
        )

        result = await session.execute(statement)
        todo = result.scalar_one_or_none()

        if not todo:
            logger.warning(f"Todo not found or access denied for update: {todo_id} for user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo not found"
            )

        # Update only provided fields (partial update)
        update_data = todo_data.model_dump(exclude_unset=True)

        # Convert timezone-aware datetime to timezone-naive for PostgreSQL compatibility
        if 'due_date' in update_data and update_data['due_date'] is not None:
            if update_data['due_date'].tzinfo is not None:
                # Remove timezone info to match created_at/updated_at
                update_data['due_date'] = update_data['due_date'].replace(tzinfo=None)

        for field, value in update_data.items():
            setattr(todo, field, value)

        # Update timestamp
        todo.updated_at = datetime.utcnow()

        session.add(todo)
        await session.commit()
        await session.refresh(todo)

        logger.info(f"Todo updated: {todo_id} for user: {user_id}")
        return TodoResponse.model_validate(todo)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to update todo {todo_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update todo"
        )


@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a todo",
    description="Permanently deletes a todo. Returns 404 if todo doesn't exist or doesn't belong to authenticated user.",
    responses={
        204: {"description": "Todo deleted successfully (no content)"},
        404: {"description": "Todo not found or doesn't belong to user"}
    }
)
async def delete_todo(
    todo_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> None:
    """
    Delete a todo permanently.

    Security:
    - Only deletes todo if it belongs to authenticated user
    - Returns 404 if todo doesn't exist or doesn't belong to user

    Args:
        todo_id: UUID of the todo to delete
        user_id: Automatically extracted from JWT token
        session: Database session

    Returns:
        None (204 No Content)

    Raises:
        HTTPException(404): If todo not found or doesn't belong to user
    """
    try:
        # Query todo with BOTH id and user_id filters (CRITICAL: user isolation)
        statement = select(Todo).where(
            col(Todo.id) == todo_id,
            col(Todo.user_id) == user_id
        )

        result = await session.execute(statement)
        todo = result.scalar_one_or_none()

        if not todo:
            logger.warning(f"Todo not found or access denied for deletion: {todo_id} for user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo not found"
            )

        await session.delete(todo)
        await session.commit()

        logger.info(f"Todo deleted: {todo_id} for user: {user_id}")

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to delete todo {todo_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete todo"
        )


@router.patch(
    "/{todo_id}/complete",
    response_model=TodoResponse,
    summary="Toggle todo completion status",
    description="Toggles the completion status of a todo (complete ↔ incomplete). Returns 404 if todo doesn't exist or doesn't belong to authenticated user.",
    responses={
        200: {"description": "Todo completion status toggled successfully"},
        404: {"description": "Todo not found or doesn't belong to user"}
    }
)
async def toggle_todo_completion(
    todo_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> TodoResponse:
    """
    Toggle the completion status of a todo.

    Security:
    - Only toggles todo if it belongs to authenticated user
    - Returns 404 if todo doesn't exist or doesn't belong to user

    Args:
        todo_id: UUID of the todo to toggle
        user_id: Automatically extracted from JWT token
        session: Database session

    Returns:
        TodoResponse: Updated todo with toggled completion status

    Raises:
        HTTPException(404): If todo not found or doesn't belong to user
    """
    try:
        # Query todo with BOTH id and user_id filters (CRITICAL: user isolation)
        statement = select(Todo).where(
            col(Todo.id) == todo_id,
            col(Todo.user_id) == user_id
        )

        result = await session.execute(statement)
        todo = result.scalar_one_or_none()

        if not todo:
            logger.warning(f"Todo not found or access denied for toggle: {todo_id} for user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo not found"
            )

        # Toggle completion status
        todo.is_completed = not todo.is_completed
        todo.updated_at = datetime.utcnow()

        session.add(todo)
        await session.commit()
        await session.refresh(todo)

        logger.info(f"Todo completion toggled: {todo_id} (now {todo.is_completed}) for user: {user_id}")
        return TodoResponse.model_validate(todo)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to toggle todo {todo_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle todo completion"
        )
