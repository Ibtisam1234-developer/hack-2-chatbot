export interface Todo {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  category: string | null;
  due_date: string | null;
  is_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface TodoCreate {
  title: string;
  description?: string | null;
  category?: string | null;
  due_date?: string | null;
  is_completed?: boolean;
}

export interface TodoUpdate {
  title?: string;
  description?: string | null;
  category?: string | null;
  due_date?: string | null;
  is_completed?: boolean;
}
