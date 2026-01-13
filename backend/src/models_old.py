"""
Task Data Model for Interactive Todo Application

Owner: Service Logic Agent
Purpose: Task entity definition, enums, and structured models for task management

Constitutional Constraints:
- ALLOWED: Data model definitions, conversion methods
- FORBIDDEN: User input (input()), User output (print()), Database connections, Business logic
"""

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class Priority(str, Enum):
    """Priority levels for tasks."""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class RecurrenceInterval(str, Enum):
    """Recurrence interval for tasks."""
    NONE = 'none'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'


class TaskStatus(str, Enum):
    """Completion status for tasks."""
    PENDING = 'pending'
    COMPLETED = 'completed'


class TaskCreate(BaseModel):
    """Schema for creating a new task."""
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    category: Optional[str] = None
    due_date: Optional[datetime] = None
    recurrence_interval: RecurrenceInterval = RecurrenceInterval.NONE

    model_config = ConfigDict(use_enum_values=True)


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[Priority] = None
    category: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[TaskStatus] = None
    recurrence_interval: Optional[RecurrenceInterval] = None

    model_config = ConfigDict(use_enum_values=True)


class Task(BaseModel):
    """
    Task entity representing a todo item.

    Attributes:
        id: Unique task identifier
        title: Task title (1-255 characters)
        description: Optional detailed description
        priority: Priority level (low, medium, high)
        category: Optional category name
        due_date: Optional due date timestamp
        status: Task completion status (pending, completed)
        recurrence_interval: Recurrence interval (daily, weekly, monthly, none)
        parent_task_id: Reference to parent task (for recurring task instances)
        reminder_sent: Whether notification sent
        created_at: Creation timestamp
        updated_at: Last modification timestamp

    Constitutional Compliance:
        ✅ Pure data model (no behavior)
        ✅ NO user interaction
        ✅ NO database access
    """
    id: int
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    category: Optional[str] = None
    due_date: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    recurrence_interval: RecurrenceInterval = RecurrenceInterval.NONE
    parent_task_id: Optional[int] = None
    reminder_sent: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)

    def to_dict(self) -> dict:
        """
        Convert Task to dictionary representation.

        Returns:
            Dictionary with all task fields, timestamps in ISO format
        """
        return self.model_dump()

    @classmethod
    def from_db_row(cls, row: tuple) -> 'Task':
        """
        Create Task from database row tuple.

        Args:
            row: Database row as tuple.
                 Expects: (id, title, description, priority, category, due_date, is_completed, recurrence_interval, parent_task_id, reminder_sent, created_at, updated_at)

        Returns:
            Task instance populated from database row
        """
        # Convert boolean is_completed to TaskStatus enum
        is_completed = row[6]
        status = TaskStatus.COMPLETED if is_completed else TaskStatus.PENDING

        return cls(
            id=row[0],
            title=row[1],
            description=row[2],
            priority=Priority(row[3]),
            category=row[4],
            due_date=row[5],
            status=status,
            recurrence_interval=RecurrenceInterval(row[7]),
            parent_task_id=row[8],
            reminder_sent=row[9],
            created_at=row[10],
            updated_at=row[11]
        )

    def __str__(self) -> str:
        """String representation for display."""
        icon = "✓" if self.status == TaskStatus.COMPLETED else "○"
        priority_tag = f" [{self.priority.upper()}]"
        due_tag = f" (Due: {self.due_date.strftime('%Y-%m-%d')})" if self.due_date else ""
        return f"[{icon}]{priority_tag} #{self.id}: {self.title}{due_tag}"
