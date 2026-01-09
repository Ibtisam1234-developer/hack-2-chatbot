"""
Service Layer for Interactive Todo Application (v2.0.0)

Owner: Service Logic Agent
Purpose: Business logic orchestration, validation, and error translation
Architecture: Async/Await with Pydantic models

Constitutional Constraints:
- ALLOWED: Business rule validation, orchestration between CLI and Repository, error handling
- FORBIDDEN: Direct database connections (uses repository.py), User input (input()),
             User output (print()), SQL queries, Rich UI output.

All service functions return dictionaries with consistent structure:
- {'success': bool, 'message': str, 'data': Any | None}
"""

import logging
import dateparser
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from src.models import Task, TaskCreate, TaskUpdate, TaskStatus, RecurrenceInterval, Priority
import src.repository as repository
from src.recurrence_engine import create_recurring_task_instance

logger = logging.getLogger("services")

def parse_natural_date(date_str: str) -> Optional[datetime]:
    """
    Parse natural language date string into datetime object.

    Args:
        date_str: Human-readable date string

    Returns:
        Datetime object or None if parsing fails
    """
    if not date_str or not date_str.strip():
        return None

    # dateparser configuration
    settings = {
        'RETURN_AS_TIMEZONE_AWARE': False,  # Store as local/naive for now to match project simple datetime usage
        'PREFER_DATES_FROM': 'future',
        'PREFER_DAY_OF_MONTH': 'current'
    }

    try:
        parsed_date = dateparser.parse(date_str, settings=settings)
        return parsed_date
    except Exception as e:
        logger.warning(f"Failed to parse date string '{date_str}': {e}")
        return None

async def create_task(task_data: TaskCreate) -> Dict[str, Any]:
    """
    Orchestrate task creation with validation.

    Args:
        task_data: Pydantic model containing task creation fields

    Returns:
        Dict with success status, message, and created task data
    """
    try:
        # Pydantic already handled basic type validation and length constraints via TaskCreate
        # Extract data and call repository
        new_task = await repository.create_task(
            title=task_data.title.strip(),
            description=task_data.description.strip() if task_data.description else None,
            priority=task_data.priority,
            category=task_data.category.strip() if task_data.category else None,
            due_date=task_data.due_date,
            recurrence_interval=task_data.recurrence_interval
        )

        return {
            "success": True,
            "message": f"Task '{new_task.title}' created successfully.",
            "data": new_task
        }
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return {
            "success": False,
            "message": f"Failed to create task: {str(e)}",
            "data": None
        }

async def get_tasks(
    status: Optional[TaskStatus] = None,
    category: Optional[str] = None,
    priority: Optional[Priority] = None,
    parent_task_id: Optional[int] = None,
    recurrence_interval: Optional[str] = None,
    due_before: Optional[datetime] = None,
    due_after: Optional[datetime] = None,
    sort_by: str = 'date'
) -> Dict[str, Any]:
    """
    Retrieve tasks with filtering and sorting.

    Args:
        status: Filter by completion status
        category: Filter by category name
        priority: Filter by priority level
        parent_task_id: Filter by parent task
        recurrence_interval: Filter by recurrence interval
        due_before: Filter by due date before
        due_after: Filter by due date after
        sort_by: Sorting criterion ('date', 'alpha', 'priority')

    Returns:
        Dict with success status, message, and list of tasks
    """
    try:
        # Normalize status and priority to string values for repository
        status_val = status
        if status and hasattr(status, 'value'):
            status_val = status.value
        elif status:
            status_val = str(status)

        priority_val = priority
        if priority and hasattr(priority, 'value'):
            priority_val = priority.value
        elif priority:
            priority_val = str(priority)

        tasks = await repository.get_all_tasks(
            status=status_val,
            category=category,
            priority=priority_val,
            parent_task_id=parent_task_id,
            recurrence_interval=recurrence_interval,
            due_before=due_before,
            due_after=due_after,
            sort_by=sort_by
        )

        return {
            "success": True,
            "message": f"Retrieved {len(tasks)} tasks.",
            "data": tasks
        }
    except Exception as e:
        logger.error(f"Error retrieving tasks: {e}")
        return {
            "success": False,
            "message": f"Failed to retrieve tasks: {str(e)}",
            "data": []
        }

async def update_task(task_id: int, update_data: TaskUpdate) -> Dict[str, Any]:
    """
    Update an existing task with validation.

    Args:
        task_id: ID of the task to update
        update_data: Pydantic model containing update fields

    Returns:
        Dict with success status, message, and updated task data
    """
    try:
        # Business Validation: Ensure task exists
        existing_task = await repository.get_task_by_id(task_id)
        if not existing_task:
            return {
                "success": False,
                "message": f"Task with ID {task_id} not found.",
                "data": None
            }

        # Convert Pydantic model to dict, excluding unset fields
        updates = update_data.model_dump(exclude_unset=True)
        if not updates:
            return {
                "success": True,
                "message": "No changes requested.",
                "data": existing_task
            }

        # Handle string stripping for updates
        if 'title' in updates and updates['title']:
            updates['title'] = updates['title'].strip()
        if 'description' in updates and updates['description']:
            updates['description'] = updates['description'].strip()
        if 'category' in updates and updates['category']:
            updates['category'] = updates['category'].strip()

        updated_task = await repository.update_task(task_id, **updates)

        return {
            "success": True,
            "message": f"Task {task_id} updated successfully.",
            "data": updated_task
        }
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        return {
            "success": False,
            "message": f"Failed to update task: {str(e)}",
            "data": None
        }

async def delete_task(task_id: int) -> Dict[str, Any]:
    """
    Delete a task.

    Args:
        task_id: ID of the task to delete

    Returns:
        Dict with success status and message
    """
    try:
        # Business Validation: Ensure task exists
        existing_task = await repository.get_task_by_id(task_id)
        if not existing_task:
            return {
                "success": False,
                "message": f"Task with ID {task_id} not found.",
                "data": None
            }

        success = await repository.delete_task(task_id)
        if success:
            return {
                "success": True,
                "message": f"Task {task_id} deleted successfully.",
                "data": None
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete task {task_id}.",
                "data": None
            }
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        return {
            "success": False,
            "message": f"Error during deletion: {str(e)}",
            "data": None
        }

async def search_tasks(query: str) -> Dict[str, Any]:
    """
    Search for tasks by query string.

    Args:
        query: Search term

    Returns:
        Dict with success status, message, and matching tasks
    """
    if not query or not query.strip():
        return {
            "success": False,
            "message": "Search query cannot be empty.",
            "data": []
        }

    try:
        tasks = await repository.search_tasks(query.strip())
        return {
            "success": True,
            "message": f"Found {len(tasks)} tasks matching '{query}'.",
            "data": tasks
        }
    except Exception as e:
        logger.error(f"Error searching tasks for '{query}': {e}")
        return {
            "success": False,
            "message": f"Search failed: {str(e)}",
            "data": []
        }

async def toggle_task_completion(task_id: int) -> Dict[str, Any]:
    """
    Toggle the completion status of a task.

    Args:
        task_id: ID of the task to toggle

    Returns:
        Dict with success status, message, and updated task data
    """
    try:
        existing_task = await repository.get_task_by_id(task_id)
        if not existing_task:
            return {
                "success": False,
                "message": f"Task with ID {task_id} not found.",
                "data": None
            }

        # Determine new status
        is_completed = (existing_task.status == TaskStatus.PENDING)
        new_status = TaskStatus.COMPLETED if is_completed else TaskStatus.PENDING

        updated_task = await repository.update_task(task_id, status=new_status)

        # Trigger recurrence logic if marking as completed
        new_task_msg = ""
        if is_completed and updated_task.recurrence_interval != RecurrenceInterval.NONE:
            new_instance_id = await create_recurring_task_instance(
                completed_task_id=task_id,
                current_due_date=updated_task.due_date,
                recurrence_interval=updated_task.recurrence_interval
            )
            if new_instance_id:
                new_task_msg = f" New recurring instance created: {new_instance_id}."

        status_str = "completed" if is_completed else "pending"
        return {
            "success": True,
            "message": f"Task {task_id} marked as {status_str}.{new_task_msg}",
            "data": updated_task
        }
    except Exception as e:
        logger.error(f"Error toggling task {task_id}: {e}")
        return {
            "success": False,
            "message": f"Failed to toggle status: {str(e)}",
            "data": None
        }

async def get_task_history(root_task_id: int) -> Dict[str, Any]:
    """
    Get all instances of a recurring task series.

    Args:
        root_task_id: ID of the root task

    Returns:
        Dict with success status, message, and list of tasks
    """
    try:
        tasks = await repository.get_task_history(root_task_id)
        if not tasks:
            return {
                "success": False,
                "message": f"No history found for task {root_task_id}.",
                "data": []
            }

        return {
            "success": True,
            "message": f"Found {len(tasks)} instances in series.",
            "data": tasks
        }
    except Exception as e:
        logger.error(f"Error retrieving task history for {root_task_id}: {e}")
        return {
            "success": False,
            "message": f"Failed to retrieve history: {str(e)}",
            "data": []
        }
