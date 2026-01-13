// components/chat/ChatInterface.tsx
"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { sendMessage, getConversation } from "@/lib/chat-client";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import type { Message, ChatInterfaceProps } from "@/types/chat";

export function ChatInterface({
  userId,
  conversationId: initialConversationId,
  initialMessages = [],
  onConversationCreated,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<number | undefined>(
    initialConversationId
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Fetch message history when conversation ID changes
  useEffect(() => {
    async function fetchHistory() {
      if (!initialConversationId || !userId) {
        setMessages([]);
        return;
      }

      try {
        setIsLoadingHistory(true);
        setError(null);
        const conversation = await getConversation(userId, initialConversationId);
        setMessages(conversation.messages);
        setConversationId(initialConversationId);
      } catch (err) {
        console.error("Failed to fetch conversation history:", err);
        setError("Failed to load conversation history. Please try again.");
        setMessages([]);
      } finally {
        setIsLoadingHistory(false);
      }
    }

    fetchHistory();
  }, [initialConversationId, userId]);

  // Scroll to bottom when messages change
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSubmit = async () => {
    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading) return;

    setError(null);
    setIsLoading(true);

    // Add user message optimistically
    const userMessage: Message = {
      id: Date.now(),
      role: "user",
      content: trimmedInput,
      tool_calls: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const response = await sendMessage(userId, trimmedInput, conversationId);

      // Update conversation ID if new
      if (!conversationId && response.conversation_id) {
        setConversationId(response.conversation_id);
        onConversationCreated?.(response.conversation_id);
      }

      // Add assistant message
      const assistantMessage: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: response.response,
        tool_calls: response.tool_calls,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to send message";
      setError(errorMessage);
      // Remove optimistic user message on error
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
      setInput(trimmedInput); // Restore input
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    setError(null);
    if (input.trim()) {
      handleSubmit();
    }
  };

  const handleClearError = () => {
    setError(null);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-xl shadow-lg border border-purple-100">
      {/* Messages Area */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4"
        role="log"
        aria-label="Chat messages"
        aria-live="polite"
      >
        {isLoadingHistory ? (
          <LoadingState message="Loading conversation..." />
        ) : messages.length === 0 ? (
          <EmptyState />
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}

        {/* Loading indicator for AI response */}
        {isLoading && <TypingIndicator />}

        <div ref={messagesEndRef} />
      </div>

      {/* Error Message */}
      {error && (
        <ErrorBanner
          message={error}
          onRetry={handleRetry}
          onDismiss={handleClearError}
          canRetry={!!input.trim()}
        />
      )}

      {/* Input Area */}
      <ChatInput
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        disabled={isLoading}
        placeholder="Ask me to help manage your tasks..."
      />
    </div>
  );
}

function LoadingState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mb-4" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 px-4">
      <div className="w-16 h-16 bg-gradient-to-br from-purple-100 to-blue-100 rounded-full flex items-center justify-center mb-4">
        <svg
          className="w-8 h-8 text-purple-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-gray-700 mb-2">
        Start a conversation
      </h3>
      <p className="text-sm max-w-sm mb-4">
        I can help you manage your tasks using natural language. Try one of these:
      </p>
      <div className="space-y-2 text-sm">
        <SuggestionChip text="Add a task to buy groceries" />
        <SuggestionChip text="Show my pending tasks" />
        <SuggestionChip text="Mark my first task as complete" />
      </div>
    </div>
  );
}

function SuggestionChip({ text }: { text: string }) {
  return (
    <div className="inline-block bg-purple-50 text-purple-700 px-3 py-1.5 rounded-full text-xs border border-purple-200">
      "{text}"
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-start space-x-3" role="status" aria-label="AI is typing">
      <div className="w-8 h-8 bg-gradient-to-br from-purple-400 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
        <svg
          className="w-4 h-4 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>
      </div>
      <div className="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3">
        <div className="flex space-x-1">
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
          <div
            className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
            style={{ animationDelay: "0.1s" }}
          />
          <div
            className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
            style={{ animationDelay: "0.2s" }}
          />
        </div>
      </div>
    </div>
  );
}

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  onDismiss: () => void;
  canRetry?: boolean;
}

function ErrorBanner({ message, onRetry, onDismiss, canRetry = false }: ErrorBannerProps) {
  return (
    <div className="px-4 py-3 bg-red-50 border-t border-red-200" role="alert">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <svg
            className="w-5 h-5 text-red-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-sm text-red-700">{message}</p>
        </div>
        <div className="flex items-center space-x-2">
          {canRetry && onRetry && (
            <button
              onClick={onRetry}
              className="text-sm text-red-600 hover:text-red-800 font-medium focus:outline-none focus:ring-2 focus:ring-red-300 rounded px-2 py-1"
            >
              Retry
            </button>
          )}
          <button
            onClick={onDismiss}
            className="text-red-400 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-300 rounded p-1"
            aria-label="Dismiss error"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatInterface;
