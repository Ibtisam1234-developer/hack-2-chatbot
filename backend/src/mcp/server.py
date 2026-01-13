# backend/src/mcp/server.py
"""
FastMCP Server for AI Chatbot Task Management

Owner: MCP Engineer
Purpose: MCP tool server for AI agent task operations
Architecture: FastMCP with FastAPI integration

Constitutional Constraints:
- REQUIRED: All tools enforce user_id isolation (Principle IV)
- REQUIRED: Tools are the ONLY way AI accesses data (Principle VII)
- REQUIRED: All tool calls logged for audit trail (Principle VIII)
"""

import logging

logger = logging.getLogger("mcp.server")

# Import the mcp instance from task_tools (tools are registered there)
from .tools.task_tools import mcp, add_task, list_tasks, complete_task, update_task, delete_task

# Re-export as mcp_server for consistency
mcp_server = mcp

logger.info("FastMCP server 'task-tools' initialized with tools: add_task, list_tasks, complete_task, update_task, delete_task")

__all__ = ["mcp_server", "add_task", "list_tasks", "complete_task", "update_task", "delete_task"]
