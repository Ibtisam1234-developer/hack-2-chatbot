"""
Notification Manager for Interactive Todo Application

Owner: Service Logic Agent
Purpose: Handle cross-platform desktop notifications and boot checks for due tasks
Architecture: 100% async/await, graceful degradation if plyer unsupported

Constitutional Compliance:
- ✅ Service Logic Agent ownership
- ✅ NO database connections (must use repository layer)
- ✅ NO user interaction (input(), print())
- ✅ NO Rich UI (system notifications only)
- ✅ All functions async
- ✅ Graceful degradation if notifications unsupported
"""

import logging
from datetime import datetime, timedelta
from plyer import notification
from src.repository import get_all_tasks, update_task

logger = logging.getLogger("notification_manager")

async def show_notification(title: str, message: str) -> bool:
    """
    Display cross-platform desktop notification.

    Args:
        title: Notification title
        message: Notification message body

    Returns:
        True if successful, False otherwise
    """
    try:
        # notification.notify is a synchronous call but usually very fast
        #plyer handles platform-specific details internally
        notification.notify(
            title=title,
            message=message,
            app_name="Todo CLI",
            timeout=10  # seconds
        )
        return True
    except Exception as e:
        # Catch silently as per constraints
        logger.warning(f"OS notification failed: {e}")
        return False

async def check_due_tasks_and_notify() -> int:
    """
    Find tasks due within 30 minutes and send notifications.

    Returns:
        Number of tasks notified
    """
    try:
        now = datetime.now()
        time_threshold = now + timedelta(minutes=30)

        # Query all tasks (we'll filter in memory for precision)
        tasks = await get_all_tasks(status='pending')

        # Filter for tasks due within 30 minutes that haven't been notified
        due_tasks = [
            t for t in tasks
            if t.due_date
            and t.due_date >= now  # Only upcoming ones
            and t.due_date <= time_threshold
            and not t.reminder_sent
        ]

        if not due_tasks:
            return 0

        # Send notification
        if len(due_tasks) == 1:
            task = due_tasks[0]
            title = "Task Due Soon"
            message = f"'{task.title}' is due at {task.due_date.strftime('%H:%M')}"
        else:
            title = f"{len(due_tasks)} Tasks Due Soon"
            message = f"You have Multiple tasks due within 30 minutes."

        # Show notification (silent failure if daemon missing)
        await show_notification(title, message)

        # Mark as notified in database
        for task in due_tasks:
            await update_task(task.id, reminder_sent=True)

        logger.info(f"Notified about {len(due_tasks)} upcoming tasks.")
        return len(due_tasks)

    except Exception as e:
        logger.error(f"Error during due task check: {e}")
        return 0
