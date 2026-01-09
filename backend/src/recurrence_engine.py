"""
Recurrence Engine for Interactive Todo Application

Owner: Service Logic Agent
Purpose: Calculate next due dates and manage recurring task instances
Architecture: 100% async/await, interval-based arithmetic

Constitutional Compliance:
- ✅ Service Logic Agent ownership
- ✅ NO database connections (must use repository layer)
- ✅ NO user interaction (input(), print())
- ✅ NO Rich UI (business logic only)
- ✅ All functions async
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from dateutil.relativedelta import relativedelta
from src.models import TaskCreate, RecurrenceInterval
from src.repository import get_task_by_id, create_task, update_task

logger = logging.getLogger("recurrence_engine")

async def calculate_next_due_date(
    current_due_date: datetime,
    recurrence_interval: str
) -> Optional[datetime]:
    """
    Calculate next occurrence based on recurrence interval.

    Args:
        current_due_date: Current task's due date
        recurrence_interval: Interval string (daily, weekly, monthly, none)

    Returns:
        Next due date or None if interval is none
    """
    if recurrence_interval == RecurrenceInterval.DAILY:
        return current_due_date + timedelta(days=1)
    elif recurrence_interval == RecurrenceInterval.WEEKLY:
        return current_due_date + relativedelta(weeks=1)
    elif recurrence_interval == RecurrenceInterval.MONTHLY:
        return current_due_date + relativedelta(months=1)
    else:  # "none" or invalid
        return None

async def create_recurring_task_instance(
    completed_task_id: int,
    current_due_date: Optional[datetime],
    recurrence_interval: str
) -> Optional[int]:
    """
    Create new pending instance when recurring task completed.

    Args:
        completed_task_id: ID of the just-completed task
        current_due_date: Due date of completed task
        recurrence_interval: Recurrence interval string

    Returns:
        ID of newly created task or None
    """
    # Skip if no recurrence or invalid
    if recurrence_interval == RecurrenceInterval.NONE or recurrence_interval is None:
        return None

    # Fetch completed task details
    completed_task = await get_task_by_id(completed_task_id)
    if not completed_task:
        logger.warning(f"Failed to find completed task {completed_task_id} for recurrence")
        return None

    # Calculate next due date
    next_due_date = None
    if current_due_date:
        next_due_date = await calculate_next_due_date(
            current_due_date,
            recurrence_interval
        )

    # Process creation logic
    try:
        # Create new pending instance with same attributes
        created_task = await create_task(
            title=completed_task.title,
            description=completed_task.description,
            priority=completed_task.priority.value,
            category=completed_task.category,
            due_date=next_due_date,
            recurrence_interval=recurrence_interval,
            parent_task_id=completed_task_id
        )

        if created_task:
            logger.info(f"Created recurring task instance: {created_task.id} (parent: {completed_task_id})")
            return created_task.id

    except Exception as e:
        logger.error(f"Failed to create recurring task instance: {e}")
        return None

    return None
