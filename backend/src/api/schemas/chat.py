# backend/src/api/schemas/chat.py
"""
Chat API Schemas

Owner: Backend API Engineer
Purpose: Pydantic models for chat API request/response validation
Architecture: Per contracts/chat-api.yaml specification
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for POST /api/{user_id}/chat"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The user's message to the AI assistant"
    )
    conversation_id: Optional[int] = Field(
        default=None,
        description="Optional conversation ID to continue. If omitted, creates new conversation."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Add a task to buy groceries",
                "conversation_id": None
            }
        }


class ToolCallSchema(BaseModel):
    """Schema for tool call information in responses"""
    tool: str = Field(..., description="Name of the MCP tool called")
    arguments: str = Field(..., description="JSON string of arguments passed to the tool")
    result: str = Field(..., description="Result returned by the tool")

    class Config:
        json_schema_extra = {
            "example": {
                "tool": "add_task",
                "arguments": '{"title": "Buy groceries"}',
                "result": "Task 'Buy groceries' added with ID 15."
            }
        }


class ChatResponse(BaseModel):
    """Response model for POST /api/{user_id}/chat"""
    conversation_id: int = Field(..., description="The conversation ID (new or existing)")
    response: str = Field(..., description="The AI assistant's response text")
    tool_calls: Optional[list[ToolCallSchema]] = Field(
        default=None,
        description="List of tool calls made by the AI"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": 42,
                "response": "I've added 'Buy groceries' to your task list.",
                "tool_calls": [
                    {
                        "tool": "add_task",
                        "arguments": '{"title": "Buy groceries"}',
                        "result": "Task 'Buy groceries' added with ID 15."
                    }
                ]
            }
        }


class MessageSchema(BaseModel):
    """Schema for message in conversation history"""
    id: int
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str
    tool_calls: Optional[list[ToolCallSchema]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationSchema(BaseModel):
    """Schema for conversation metadata"""
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationWithMessagesSchema(ConversationSchema):
    """Schema for conversation with full message history"""
    messages: list[MessageSchema] = []
