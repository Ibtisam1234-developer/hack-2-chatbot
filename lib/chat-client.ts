// lib/chat-client.ts
/**
 * Chat API Client
 *
 * Purpose: Client-side functions for AI chat operations
 * Architecture: Uses apiClient for authenticated requests
 */

import { apiClient } from "./api-client";

export interface ToolCall {
  tool: string;
  arguments: string;
  result: string;
}

export interface ChatResponse {
  conversation_id: number;
  response: string;
  tool_calls: ToolCall[] | null;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  tool_calls: ToolCall[] | null;
  created_at: string;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

/**
 * Send a message to the AI assistant
 *
 * @param userId - The authenticated user's ID
 * @param message - The message to send
 * @param conversationId - Optional conversation ID to continue
 * @returns ChatResponse with AI response and tool calls
 */
export async function sendMessage(
  userId: string,
  message: string,
  conversationId?: number
): Promise<ChatResponse> {
  return apiClient<ChatResponse>(`/api/${userId}/chat`, {
    method: "POST",
    body: JSON.stringify({
      message,
      conversation_id: conversationId || null,
    }),
  });
}

/**
 * Get all conversations for a user
 *
 * @param userId - The authenticated user's ID
 * @returns List of conversations
 */
export async function getConversations(userId: string): Promise<Conversation[]> {
  return apiClient<Conversation[]>(`/api/${userId}/conversations`);
}

/**
 * Get a conversation with its full message history
 *
 * @param userId - The authenticated user's ID
 * @param conversationId - The conversation ID
 * @returns Conversation with messages
 */
export async function getConversation(
  userId: string,
  conversationId: number
): Promise<ConversationWithMessages> {
  return apiClient<ConversationWithMessages>(
    `/api/${userId}/conversations/${conversationId}`
  );
}

/**
 * Delete a conversation and all its messages
 *
 * @param userId - The authenticated user's ID
 * @param conversationId - The conversation ID to delete
 */
export async function deleteConversation(
  userId: string,
  conversationId: number
): Promise<void> {
  await apiClient(`/api/${userId}/conversations/${conversationId}`, {
    method: "DELETE",
  });
}
