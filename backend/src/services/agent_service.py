# backend/src/services/agent_service.py
"""
Agent Service for AI Chatbot

Owner: AI Orchestrator
Purpose: OpenRouter LLM integration for stateless AI processing
Architecture: Stateless with AsyncOpenAI client (OpenRouter-compatible)

Constitutional Constraints:
- REQUIRED: Stateless processing (Principle VI)
- REQUIRED: Tools are the ONLY way AI accesses data (Principle VII)
- REQUIRED: All tool calls captured for audit (Principle VIII)

Note: Free tier models on OpenRouter don't support function calling.
This implementation uses structured prompts to parse tool intents from text.
"""

import os
import re
import json
import logging
from typing import Optional
from openai import AsyncOpenAI, RateLimitError, APIError

logger = logging.getLogger("services.agent_service")

# OpenRouter base URL (OpenAI-compatible API)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# System prompt for the AI agent (structured output for tool parsing)
SYSTEM_PROMPT = """You are a task management assistant. Help users manage their to-do list.

VALID ACTIONS: ADD_TASK, LIST_TASKS, COMPLETE_TASK, UPDATE_TASK, DELETE_TASK

RULES:
1. Use ONLY these 5 actions. Never use other action names.
2. Output ONE command block per response.
3. COMPLETE_TASK, UPDATE_TASK, DELETE_TASK require a task_id from the user's message.
4. Task IDs are UUIDs like "85fcb698-ab86-4255-80f7-d3a0aef307f6" - ONLY use IDs the user provides.
5. If user wants to complete/update/delete but didn't provide an ID, DO NOT output a command. Ask them to say "show tasks" first.
6. NEVER invent or guess task IDs. If no valid UUID is in the user's message, ask for it.

COMMAND FORMAT (copy exactly):
```command
ACTION: ACTION_NAME
PARAMS: {"key": "value"}
```

EXAMPLES:

User: "add buy milk"
```command
ACTION: ADD_TASK
PARAMS: {"title": "buy milk"}
```

User: "show tasks"
```command
ACTION: LIST_TASKS
PARAMS: {"status": "all"}
```

User: "complete 85fcb698-ab86-4255-80f7-d3a0aef307f6"
```command
ACTION: COMPLETE_TASK
PARAMS: {"task_id": "85fcb698-ab86-4255-80f7-d3a0aef307f6"}
```

User: "update 85fcb698-ab86-4255-80f7-d3a0aef307f6 to buy organic milk"
```command
ACTION: UPDATE_TASK
PARAMS: {"task_id": "85fcb698-ab86-4255-80f7-d3a0aef307f6", "title": "buy organic milk"}
```

User: "delete 85fcb698-ab86-4255-80f7-d3a0aef307f6"
```command
ACTION: DELETE_TASK
PARAMS: {"task_id": "85fcb698-ab86-4255-80f7-d3a0aef307f6"}
```

User: "delete my task" (no UUID provided)
I need the task ID. Say "show tasks" to see your tasks with their IDs, then tell me which to delete.

User: "update the milk task" (no UUID provided)
I need the task ID to update it. Say "show tasks" to see your tasks with their IDs.

User: "hello"
Hi! I can help manage your tasks. Say "add [task]" to create, "show tasks" to list, or provide a task ID to complete/update/delete."""


class AgentService:
    """
    Stateless AI agent service using OpenRouter API (OpenAI-compatible).

    Per Constitution Principle VI: No local session state.
    All context is passed in via conversation_history parameter.

    Note: Free tier models don't support function calling, so we use
    structured prompts and parse commands from text responses.
    """

    # Regex pattern to extract command blocks from AI response
    # Handles both wrapped (```command...```) and unwrapped formats
    COMMAND_PATTERN = re.compile(
        r'(?:```command\s*\n)?'  # Optional opening wrapper
        r'ACTION:\s*(\w+)\s*\n'
        r'PARAMS:\s*(\{.*?\})'
        r'(?:\s*\n```)?',  # Optional closing wrapper
        re.IGNORECASE | re.DOTALL
    )

    # Map action names to tool names
    ACTION_TO_TOOL = {
        "ADD_TASK": "add_task",
        "CREATE_TASK": "add_task",  # Alias
        "LIST_TASKS": "list_tasks",
        "READ_TASK": "list_tasks",  # Alias - LLM sometimes uses this
        "READ_TASKS": "list_tasks",  # Alias
        "SHOW_TASKS": "list_tasks",  # Alias
        "GET_TASKS": "list_tasks",  # Alias
        "COMPLETE_TASK": "complete_task",
        "MARK_COMPLETE": "complete_task",  # Alias
        "UPDATE_TASK": "update_task",
        "EDIT_TASK": "update_task",  # Alias
        "DELETE_TASK": "delete_task",
        "REMOVE_TASK": "delete_task",  # Alias
    }

    # Actions that require a task_id (including aliases)
    ACTIONS_REQUIRING_ID = {
        "COMPLETE_TASK", "MARK_COMPLETE",
        "UPDATE_TASK", "EDIT_TASK",
        "DELETE_TASK", "REMOVE_TASK"
    }

    def __init__(self):
        """Initialize the OpenRouter client."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL
        )
        # Default to Qwen 2.5 7B - better instruction following than Llama 3B
        self.model = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct:free")
        logger.info(f"AgentService initialized with OpenRouter model: {self.model}")

    def _parse_commands(self, text: str) -> list[tuple[str, dict]]:
        """
        Parse command blocks from AI response text.
        Only returns the FIRST valid command found to prevent multiple actions.

        Returns:
            List with at most one (action_name, params_dict) tuple
        """
        commands = []
        match = self.COMMAND_PATTERN.search(text)  # Only find first match
        if match:
            action = match.group(1).upper().strip()
            # Skip empty or invalid actions
            if not action or action not in self.ACTION_TO_TOOL:
                logger.warning(f"Skipping invalid/empty action: '{action}'")
                return commands
            try:
                params = json.loads(match.group(2))
            except json.JSONDecodeError:
                params = {}
            commands.append((action, params))
        return commands

    def _validate_command(self, action: str, params: dict) -> tuple[bool, str]:
        """
        Validate that a command has all required parameters.

        Args:
            action: The action name (e.g., "COMPLETE_TASK")
            params: The parameters dict

        Returns:
            Tuple of (is_valid, error_message)
        """
        if action in self.ACTIONS_REQUIRING_ID:
            task_id = params.get("task_id", "")
            if not task_id or not task_id.strip():
                return False, f"I need a task ID to {action.lower().replace('_', ' ')}. Please say 'show my tasks' first to see your tasks with their IDs."
        return True, ""

    def _clean_response(self, text: str) -> str:
        """Remove command blocks from response text for cleaner output."""
        return self.COMMAND_PATTERN.sub('', text).strip()

    def _clean_history(self, history: list[dict]) -> list[dict]:
        """
        Clean conversation history to prevent LLM confusion.

        Removes command blocks from previous assistant messages and
        limits history to prevent context overload.
        """
        cleaned = []
        # Only keep last 4 messages to prevent confusion
        recent_history = history[-4:] if len(history) > 4 else history

        for msg in recent_history:
            if msg["role"] == "assistant":
                # Remove command blocks from previous assistant responses
                clean_content = self._clean_response(msg["content"])
                # Also remove "Tool results:" sections
                if "Tool results:" in clean_content:
                    clean_content = clean_content.split("Tool results:")[0].strip()
                if clean_content:
                    cleaned.append({"role": "assistant", "content": clean_content})
            else:
                cleaned.append(msg)

        return cleaned

    async def process_message(
        self,
        user_message: str,
        conversation_history: list[dict],
        user_id: str,
        tool_executor: callable
    ) -> dict:
        """
        Process a user message statelessly (no history used).

        Args:
            user_message: The new message from user
            conversation_history: Ignored - each message is independent
            user_id: For tool authorization (passed to tool executor)
            tool_executor: Async function to execute tool calls

        Returns:
            dict with 'response' (str) and 'tool_calls' (list)
        """
        # Stateless: Only use system prompt + current message (no history)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        tool_calls_log = []

        try:
            # API call (no tools parameter - using text-based commands)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                extra_headers={
                    "HTTP-Referer": "https://todozen.app",
                    "X-Title": "TodoZen AI Assistant"
                }
            )

            assistant_content = response.choices[0].message.content or ""

            # Debug: Log raw LLM response
            logger.info(f"Raw LLM response: {assistant_content[:500]}")

            # Parse commands from response
            commands = self._parse_commands(assistant_content)
            logger.info(f"Parsed commands: {commands}")

            if commands:
                # Execute each command (should be only one due to _parse_commands)
                tool_results = []
                for action, params in commands:
                    # Validate command has required parameters
                    is_valid, error_msg = self._validate_command(action, params)
                    if not is_valid:
                        logger.warning(f"Invalid command {action}: missing task_id")
                        # Return the error message without executing the tool
                        return {
                            "response": error_msg,
                            "tool_calls": None
                        }

                    tool_name = self.ACTION_TO_TOOL.get(action)
                    if not tool_name:
                        logger.warning(f"Unknown action: {action}")
                        continue

                    tool_args = json.dumps(params)
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                    # Execute tool and get result
                    tool_result = await tool_executor(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        user_id=user_id
                    )

                    # Log tool call for audit trail
                    tool_calls_log.append({
                        "tool": tool_name,
                        "arguments": tool_args,
                        "result": tool_result
                    })
                    tool_results.append(tool_result)

                # Get follow-up response with tool results
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({
                    "role": "user",
                    "content": f"Tool results:\n" + "\n".join(tool_results) + "\n\nPlease provide a friendly summary of what was done."
                })

                follow_up = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    extra_headers={
                        "HTTP-Referer": "https://todozen.app",
                        "X-Title": "TodoZen AI Assistant"
                    }
                )
                final_response = follow_up.choices[0].message.content or ""
            else:
                # No commands - just return the response
                final_response = assistant_content

            # Clean any remaining command blocks from response
            final_response = self._clean_response(final_response)

            logger.info(f"Agent processed message with {len(tool_calls_log)} tool calls")

            return {
                "response": final_response,
                "tool_calls": tool_calls_log if tool_calls_log else None
            }

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            return {
                "response": "I'm currently experiencing high demand. Please wait a moment and try again.",
                "tool_calls": None
            }
        except APIError as e:
            logger.error(f"API error: {e}")
            return {
                "response": "I'm having trouble connecting to my AI service. Please try again in a moment.",
                "tool_calls": None
            }
        except Exception as e:
            logger.error(f"Agent processing error: {e}")
            return {
                "response": "I'm sorry, I encountered an error processing your request. Please try again.",
                "tool_calls": None
            }


# Singleton instance
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """Get or create the singleton AgentService instance."""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
