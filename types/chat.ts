// types/chat.ts
/**
 * TypeScript types for the chat feature
 *
 * These types define the data structures used for communication
 * with the backend chat API and internal state management.
 */

/**
 * Represents a tool call made by the AI assistant
 */
export interface ToolCall {
  tool: string;
  arguments: string;
  result: string;
}

/**
 * Response from the chat API endpoint
 */
export interface ChatResponse {
  conversation_id: number;
  response: string;
  tool_calls: ToolCall[] | null;
}

/**
 * Request body for sending a chat message
 */
export interface ChatRequest {
  message: string;
  conversation_id?: number | null;
}

/**
 * Represents a conversation summary (without messages)
 */
export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

/**
 * Represents a single message in a conversation
 */
export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  tool_calls: ToolCall[] | null;
  created_at: string;
}

/**
 * Represents a conversation with its full message history
 */
export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

/**
 * Props for the ChatInterface component
 */
export interface ChatInterfaceProps {
  userId: string;
  conversationId?: number;
  initialMessages?: Message[];
  onConversationCreated?: (conversationId: number) => void;
}

/**
 * Props for the MessageBubble component
 */
export interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

/**
 * Props for the ChatInput component
 */
export interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
}

/**
 * Props for the ToolCallsDisplay component
 */
export interface ToolCallsDisplayProps {
  toolCalls: ToolCall[];
}

/**
 * Chat state for managing the conversation
 */
export interface ChatState {
  messages: Message[];
  conversationId?: number;
  isLoading: boolean;
  isLoadingHistory: boolean;
  error: string | null;
}
