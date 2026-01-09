"use client";

import { useState } from "react";
import { Todo } from "@/lib/types";
import { apiClient } from "@/lib/api-client";
import { DeleteConfirmationModal } from "./DeleteConfirmationModal";

interface TodoItemProps {
  todo: Todo;
  onUpdate: (updatedTodo: Todo) => void;
  onDelete: (todoId: string) => void;
  onEdit: (todo: Todo) => void;
}

export function TodoItem({ todo, onUpdate, onDelete, onEdit }: TodoItemProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isToggling, setIsToggling] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const handleToggleComplete = async () => {
    setIsToggling(true);

    // Optimistic update
    const optimisticTodo = {
      ...todo,
      is_completed: !todo.is_completed,
      updated_at: new Date().toISOString(),
    };
    onUpdate(optimisticTodo);

    try {
      const updatedTodo = await apiClient<Todo>(
        `/api/todos/${todo.id}/complete`,
        {
          method: "PATCH",
        }
      );
      onUpdate(updatedTodo);
    } catch (error) {
      // Revert on error
      onUpdate(todo);
      console.error("Failed to toggle todo:", error);
      alert("Failed to update todo. Please try again.");
    } finally {
      setIsToggling(false);
    }
  };

  const handleDeleteClick = () => {
    setShowDeleteModal(true);
  };

  const handleDeleteConfirm = async () => {
    setShowDeleteModal(false);
    setIsDeleting(true);
    try {
      await apiClient(`/api/todos/${todo.id}`, {
        method: "DELETE",
      });
      onDelete(todo.id);
    } catch (error) {
      console.error("Failed to delete todo:", error);
      alert("Failed to delete todo. Please try again.");
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setShowDeleteModal(false);
  };

  return (
    <div
      className={`bg-white/80 backdrop-blur-sm rounded-xl shadow-md border transition-all duration-300 p-5 hover:shadow-lg group ${
        todo.is_completed
          ? "border-teal-200 bg-gradient-to-r from-teal-50/50 to-green-50/50"
          : "border-purple-100 hover:border-purple-200"
      }`}
    >
      <div className="flex items-start gap-4">
        {/* Custom Checkbox */}
        <button
          onClick={handleToggleComplete}
          disabled={isToggling}
          className={`mt-1 flex-shrink-0 w-6 h-6 rounded-lg border-2 transition-all duration-200 flex items-center justify-center ${
            todo.is_completed
              ? "bg-gradient-to-br from-teal-400 to-green-500 border-teal-500"
              : "border-purple-300 hover:border-purple-400 hover:bg-purple-50"
          } ${isToggling ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
          aria-label={todo.is_completed ? "Mark as incomplete" : "Mark as complete"}
        >
          {todo.is_completed && (
            <svg
              className="w-4 h-4 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M5 13l4 4L19 7"
              />
            </svg>
          )}
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2 mb-2">
            <h3
              className={`text-lg font-semibold transition-all duration-200 flex-1 ${
                todo.is_completed
                  ? "line-through text-gray-500"
                  : "text-gray-900"
              }`}
            >
              {todo.title}
            </h3>
            {todo.category && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 border border-purple-200">
                {todo.category}
              </span>
            )}
          </div>
          {todo.description && (
            <p
              className={`mt-2 text-sm leading-relaxed transition-all duration-200 ${
                todo.is_completed ? "text-gray-400" : "text-gray-600"
              }`}
            >
              {todo.description}
            </p>
          )}
          <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 flex-wrap">
            {todo.due_date && (
              <div className={`flex items-center space-x-1 ${
                new Date(todo.due_date) < new Date() && !todo.is_completed
                  ? "text-red-500 font-medium"
                  : ""
              }`}>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span>
                  Due: {new Date(todo.due_date).toLocaleDateString()} at {new Date(todo.due_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            )}
            <div className="flex items-center space-x-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>
                {new Date(todo.created_at).toLocaleDateString()}
              </span>
            </div>
            {todo.updated_at !== todo.created_at && (
              <div className="flex items-center space-x-1">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>
                  {new Date(todo.updated_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex-shrink-0 flex items-center gap-2">
          {/* Edit Button */}
          <button
            onClick={() => onEdit(todo)}
            className="p-2 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-all duration-200 opacity-0 group-hover:opacity-100"
            aria-label="Edit todo"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>

          {/* Delete Button */}
          <button
            onClick={handleDeleteClick}
            disabled={isDeleting}
            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed opacity-0 group-hover:opacity-100"
            aria-label="Delete todo"
          >
            {isDeleting ? (
              <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : (
              <svg
                className="h-5 w-5"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmationModal
        isOpen={showDeleteModal}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        todoTitle={todo.title}
      />
    </div>
  );
}
