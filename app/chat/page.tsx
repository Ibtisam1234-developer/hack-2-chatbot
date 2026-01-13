// app/chat/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/auth-client";
import { ChatInterface } from "@/components/ChatInterface";
import { getConversations, deleteConversation, Conversation } from "@/lib/chat-client";
import Link from "next/link";

export default function ChatPage() {
  const router = useRouter();
  const { data: session, isPending } = useSession();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<number | undefined>();
  const [loadingConversations, setLoadingConversations] = useState(true);

  // Check authentication
  useEffect(() => {
    if (!isPending && !session) {
      router.push("/login");
    }
  }, [session, isPending, router]);

  // Fetch conversations
  useEffect(() => {
    async function fetchConversations() {
      if (!session?.user?.id) return;

      try {
        setLoadingConversations(true);
        const convs = await getConversations(session.user.id);
        setConversations(convs);
      } catch (err) {
        console.error("Failed to fetch conversations:", err);
      } finally {
        setLoadingConversations(false);
      }
    }

    if (session) {
      fetchConversations();
    }
  }, [session]);

  const handleConversationCreated = (conversationId: number) => {
    // Refresh conversations list
    if (session?.user?.id) {
      getConversations(session.user.id).then(setConversations);
    }
    setSelectedConversationId(conversationId);
  };

  const handleNewChat = () => {
    setSelectedConversationId(undefined);
  };

  const handleDeleteConversation = async (conversationId: number, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent selecting the conversation
    if (!session?.user?.id) return;

    if (!confirm("Are you sure you want to delete this conversation?")) return;

    try {
      await deleteConversation(session.user.id, conversationId);
      // Remove from local state
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      // If this was the selected conversation, clear selection
      if (selectedConversationId === conversationId) {
        setSelectedConversationId(undefined);
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
      alert("Failed to delete conversation");
    }
  };

  // Show loading state while checking authentication
  if (isPending) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto"></div>
          <p className="mt-4 text-gray-700">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!session) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm shadow-sm border-b border-purple-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Link href="/dashboard" className="flex items-center space-x-3 hover:opacity-80 transition-opacity">
                <div className="w-10 h-10 bg-gradient-to-br from-purple-400 to-blue-500 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                    AI Assistant
                  </h1>
                  <p className="text-xs text-gray-600">
                    Manage tasks with natural language
                  </p>
                </div>
              </Link>
            </div>
            <div className="flex items-center space-x-3">
              <Link
                href="/dashboard"
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-purple-600 transition-colors"
              >
                Dashboard
              </Link>
              <button
                onClick={handleNewChat}
                className="px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all"
              >
                New Chat
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex gap-6 h-[calc(100vh-140px)]">
          {/* Sidebar - Conversation List */}
          <div className="w-72 flex-shrink-0 bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-purple-100 overflow-hidden">
            <div className="p-4 border-b border-purple-100">
              <h2 className="font-semibold text-gray-800">Conversations</h2>
            </div>
            <div className="overflow-y-auto h-[calc(100%-60px)]">
              {loadingConversations ? (
                <div className="p-4 text-center text-gray-700">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500 mx-auto"></div>
                </div>
              ) : conversations.length === 0 ? (
                <div className="p-4 text-center text-gray-700 text-sm">
                  No conversations yet. Start chatting!
                </div>
              ) : (
                <div className="divide-y divide-purple-50">
                  {conversations.map((conv) => (
                    <div
                      key={conv.id}
                      className={`group relative flex items-center hover:bg-purple-50 transition-colors ${
                        selectedConversationId === conv.id
                          ? "bg-purple-100 border-l-4 border-purple-500"
                          : ""
                      }`}
                    >
                      <button
                        onClick={() => setSelectedConversationId(conv.id)}
                        className="flex-1 p-4 text-left"
                      >
                        <p className="font-medium text-gray-800 truncate text-sm pr-8">
                          {conv.title}
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          {new Date(conv.updated_at).toLocaleDateString()}
                        </p>
                      </button>
                      <button
                        onClick={(e) => handleDeleteConversation(conv.id, e)}
                        className="absolute right-2 p-2 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Delete conversation"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Chat Interface */}
          <div className="flex-1">
            <ChatInterface
              key={selectedConversationId || "new"}
              userId={session.user?.id || ""}
              conversationId={selectedConversationId}
              onConversationCreated={handleConversationCreated}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
