"use client";

import { Todo } from "@/lib/types";
import { TodoItem } from "./TodoItem";

interface TodoListProps {
  todos: Todo[];
  onUpdate: (updatedTodo: Todo) => void;
  onDelete: (todoId: string) => void;
  onEdit: (todo: Todo) => void;
}

export function TodoList({ todos, onUpdate, onDelete, onEdit }: TodoListProps) {
  if (todos.length === 0) {
    return (
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-purple-100 p-12 text-center">
        <div className="w-16 h-16 bg-gradient-to-br from-purple-100 to-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg
            className="h-8 w-8 text-purple-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Your mind is clear</h3>
        <p className="text-gray-600">
          No todos yet. Create your first task to get started on your journey to productivity.
        </p>
      </div>
    );
  }

  // Separate completed and incomplete todos
  const incompleteTodos = todos.filter((todo) => !todo.is_completed);
  const completedTodos = todos.filter((todo) => todo.is_completed);

  return (
    <div className="space-y-6">
      {incompleteTodos.length > 0 && (
        <div>
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-2 h-2 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full"></div>
            <h2 className="text-lg font-semibold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
              Active Tasks ({incompleteTodos.length})
            </h2>
          </div>
          <div className="space-y-3">
            {incompleteTodos.map((todo) => (
              <TodoItem
                key={todo.id}
                todo={todo}
                onUpdate={onUpdate}
                onDelete={onDelete}
                onEdit={onEdit}
              />
            ))}
          </div>
        </div>
      )}

      {completedTodos.length > 0 && (
        <div>
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-2 h-2 bg-gradient-to-r from-teal-500 to-green-500 rounded-full"></div>
            <h2 className="text-lg font-semibold bg-gradient-to-r from-teal-600 to-green-600 bg-clip-text text-transparent">
              Completed ({completedTodos.length})
            </h2>
          </div>
          <div className="space-y-3">
            {completedTodos.map((todo) => (
              <TodoItem
                key={todo.id}
                todo={todo}
                onUpdate={onUpdate}
                onDelete={onDelete}
                onEdit={onEdit}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
