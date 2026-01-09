"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSession, signOut } from "@/lib/auth-client";
import { apiClient } from "@/lib/api-client";
import { Todo } from "@/lib/types";
import { TodoList } from "@/components/TodoList";
import { CreateTodoForm } from "@/components/CreateTodoForm";
import { EditTodoForm } from "@/components/EditTodoForm";

const CATEGORIES = ["All", "Work", "Personal", "Shopping", "Health", "Finance", "Education", "Other"];

export default function DashboardPage() {
  const router = useRouter();
  const { data: session, isPending } = useSession();
  const [todos, setTodos] = useState<Todo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingTodo, setEditingTodo] = useState<Todo | null>(null);

  // Check authentication
  useEffect(() => {
    if (!isPending && !session) {
      router.push("/login");
    }
  }, [session, isPending, router]);

  // Fetch todos - memoized to prevent infinite loops
  const fetchTodos = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const fetchedTodos = await apiClient<Todo[]>("/api/todos");
      setTodos(fetchedTodos);
    } catch (err) {
      console.error("Failed to fetch todos:", err);
      setError(
        err instanceof Error ? err.message : "Failed to load todos"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch todos on mount and when session changes
  useEffect(() => {
    if (session) {
      fetchTodos();
    }
  }, [session, fetchTodos]);

  const handleTodoCreated = (newTodo: Todo) => {
    setTodos((prev) => [newTodo, ...prev]);
  };

  const handleTodoUpdate = (updatedTodo: Todo) => {
    setTodos((prev) =>
      prev.map((todo) => (todo.id === updatedTodo.id ? updatedTodo : todo))
    );
  };

  const handleTodoDelete = (todoId: string) => {
    setTodos((prev) => prev.filter((todo) => todo.id !== todoId));
  };

  const handleEditTodo = (todo: Todo) => {
    setEditingTodo(todo);
    setIsEditModalOpen(true);
  };

  const handleTodoUpdated = (updatedTodo: Todo) => {
    setTodos((prev) =>
      prev.map((todo) => (todo.id === updatedTodo.id ? updatedTodo : todo))
    );
    setIsEditModalOpen(false);
    setEditingTodo(null);
  };

  const handleSignOut = async () => {
    await signOut();
    router.push("/login");
  };

  // Filter todos based on search and category
  const filteredTodos = todos.filter((todo) => {
    const matchesSearch =
      todo.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (todo.description?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false);

    const matchesCategory =
      selectedCategory === "All" ||
      (selectedCategory === "Other" && !todo.category) ||
      todo.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  // Calculate analytics
  const totalTasks = todos.length;
  const completedTasks = todos.filter((t) => t.is_completed).length;
  const pendingTasks = totalTasks - completedTasks;
  const completionPercentage = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  // Show loading state while checking authentication
  if (isPending) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
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
              <div className="w-10 h-10 bg-gradient-to-br from-purple-400 to-blue-500 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                  TodoZen
                </h1>
                <p className="text-xs text-gray-600">
                  {session.user?.email}
                </p>
              </div>
            </div>
            <button
              onClick={handleSignOut}
              className="px-4 py-2 text-sm font-medium text-purple-600 bg-white border-2 border-purple-200 rounded-lg hover:bg-purple-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-all"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-2">
            Welcome Back, {session.user?.name || "Friend"}
          </h2>
          <p className="text-gray-600">
            Let's make today productive and peaceful
          </p>
        </div>

        {/* Analytics Section */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {/* Total Tasks */}
          <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-md border border-purple-100 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Tasks</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{totalTasks}</p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-purple-100 to-blue-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
            </div>
          </div>

          {/* Completed Tasks */}
          <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-md border border-teal-100 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Completed</p>
                <p className="text-3xl font-bold text-teal-600 mt-1">{completedTasks}</p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-teal-100 to-green-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          {/* Pending Tasks */}
          <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-md border border-orange-100 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Pending</p>
                <p className="text-3xl font-bold text-orange-600 mt-1">{pendingTasks}</p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-orange-100 to-yellow-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          {/* Completion Rate */}
          <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-md border border-purple-100 p-6">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-sm font-medium text-gray-600">Completion</p>
                <p className="text-3xl font-bold text-purple-600 mt-1">{completionPercentage}%</p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-purple-100 to-pink-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${completionPercentage}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Search and Filter Section */}
        <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-md border border-purple-100 p-6 mb-6">
          {/* Search Bar */}
          <div className="mb-4">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="block w-full pl-10 pr-3 py-3 border border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                placeholder="Search tasks by title or description..."
              />
            </div>
          </div>

          {/* Category Filters */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-3">Filter by Category</p>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((category) => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    selectedCategory === category
                      ? "bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-md"
                      : "bg-white text-gray-700 border border-purple-200 hover:border-purple-300 hover:bg-purple-50"
                  }`}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Todo List */}
        {loading ? (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-purple-100 p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading your todos...</p>
          </div>
        ) : error ? (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-red-200 p-8">
            <div className="text-center">
              <svg
                className="mx-auto h-12 w-12 text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                Error loading todos
              </h3>
              <p className="mt-1 text-sm text-red-600">{error}</p>
              <button
                onClick={fetchTodos}
                className="mt-4 px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg hover:from-purple-600 hover:to-blue-600 transition-all"
              >
                Try Again
              </button>
            </div>
          </div>
        ) : (
          <TodoList
            todos={filteredTodos}
            onUpdate={handleTodoUpdate}
            onDelete={handleTodoDelete}
            onEdit={handleEditTodo}
          />
        )}
      </main>

      {/* Floating Action Button */}
      <button
        onClick={() => setIsCreateModalOpen(true)}
        className="fixed bottom-8 right-8 w-16 h-16 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-full shadow-2xl hover:from-purple-600 hover:to-blue-600 focus:outline-none focus:ring-4 focus:ring-purple-300 transform hover:scale-110 transition-all duration-200 flex items-center justify-center z-40"
        aria-label="Create new task"
      >
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      </button>

      {/* Create Task Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <CreateTodoForm
              onTodoCreated={handleTodoCreated}
              onClose={() => setIsCreateModalOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Edit Task Modal */}
      {isEditModalOpen && editingTodo && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <EditTodoForm
              todo={editingTodo}
              onTodoUpdated={handleTodoUpdated}
              onClose={() => {
                setIsEditModalOpen(false);
                setEditingTodo(null);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
