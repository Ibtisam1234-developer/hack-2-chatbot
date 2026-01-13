# backend/src/mcp/tools/__init__.py
"""MCP tools for task management."""

from .task_tools import mcp, add_task, list_tasks, complete_task, verify_task_ownership

__all__ = ["mcp", "add_task", "list_tasks", "complete_task", "verify_task_ownership"]
