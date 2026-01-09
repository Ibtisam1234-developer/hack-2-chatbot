"""
Menu/UX Layer for Interactive Todo Application

Owner: Menu/UX Agent
Purpose: Display menus, collect user input, render task lists

Constitutional Constraints:
- ALLOWED: Menu display (print()), User input (input()), Input validation, Service layer calls
- FORBIDDEN: SQL queries, Database connections, Business logic validation, Schema changes
"""

from typing import Optional
from models import Task
import services


def display_menu() -> None:
    """
    Display main menu options to user.

    Menu Options:
        1. Create New Task
        2. View All Tasks
        3. Update Task
        4. Toggle Task Completion
        5. Delete Task
        6. Exit

    Constitutional Compliance:
        ✅ Display only (no input collection)
        ✅ NO SQL queries
        ✅ NO business logic
    """
    print("\n" + "=" * 50)
    print("         INTERACTIVE TODO APPLICATION")
    print("=" * 50)
    print("1. Create New Task")
    print("2. View All Tasks")
    print("3. Update Task")
    print("4. Toggle Task Completion")
    print("5. Delete Task")
    print("6. Exit")
    print("=" * 50)


def get_menu_choice() -> str:
    """
    Get and validate menu selection from user.

    Returns:
        User's menu choice as string ('1' through '6')

    Implementation Notes:
        - Prompts user for input
        - Validates choice is in valid range (1-6)
        - Loops until valid input received
        - Returns validated choice as string

    Constitutional Compliance:
        ✅ Input validation (format only)
        ✅ NO business logic validation
        ✅ NO database operations
    """
    while True:
        choice = input("\nEnter your choice (1-6): ").strip()

        if choice in ['1', '2', '3', '4', '5', '6']:
            return choice
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")


def handle_create_task(conn) -> None:
    """
    Collect task details and create task via service layer.

    Args:
        conn: Active database connection to pass to service layer

    Implementation Notes:
        - Prompts for title (required)
        - Prompts for description (optional)
        - Validates input is non-empty for title
        - Calls services.create_task() with connection
        - Displays success or error message from service layer

    Constitutional Compliance:
        ✅ Input collection only
        ✅ Calls service layer for business logic
        ✅ NO SQL queries
        ✅ NO business validation (delegates to service layer)
    """
    print("\n--- Create New Task ---")

    # Collect title (required)
    title = input("Enter task title: ").strip()

    if not title:
        print("Error: Title cannot be empty.")
        return

    # Collect description (optional)
    description = input("Enter task description (optional, press Enter to skip): ").strip()

    # If description is empty string, pass None
    if not description:
        description = None

    # Call service layer to create task
    result = services.create_task(conn, title, description)

    # Display result from service layer
    if result['success']:
        print(f"\n✓ {result['message']}")
    else:
        print(f"\n✗ {result['message']}")


def format_task_display(task: Task) -> str:
    """
    Format task for terminal display.

    Args:
        task: Task object to format

    Returns:
        Formatted string with status icon, ID, title, and description

    Format:
        [✓] #123: Task title - Description preview...
        [○] #456: Another task

    Implementation Notes:
        - Uses ✓ for completed tasks, ○ for incomplete tasks
        - Shows task ID, title, and truncated description
        - Leverages Task.__str__() method for consistent formatting

    Constitutional Compliance:
        ✅ Display formatting only
        ✅ NO business logic
        ✅ NO database operations
    """
    return str(task)


def handle_list_tasks(conn) -> None:
    """
    Display all tasks in readable format via service layer.

    Args:
        conn: Active database connection to pass to service layer

    Implementation Notes:
        - Calls services.list_tasks() with connection
        - Formats and displays each task using format_task_display()
        - Shows count of tasks
        - Displays message if no tasks exist

    Constitutional Compliance:
        ✅ Display only
        ✅ Calls service layer for data retrieval
        ✅ NO SQL queries
        ✅ NO business logic
    """
    print("\n--- All Tasks ---")

    # Call service layer to retrieve tasks
    result = services.list_tasks(conn)

    if not result['success']:
        print(f"\n✗ {result['message']}")
        return

    tasks = result['tasks']

    if not tasks:
        print("\nNo tasks found. Create your first task!")
        return

    print(f"\nTotal tasks: {len(tasks)}\n")

    # Display each task
    for task in tasks:
        print(format_task_display(task))


def handle_update_task(conn) -> None:
    """
    Collect task ID and new details, update task via service layer.

    Args:
        conn: Active database connection to pass to service layer

    Implementation Notes:
        - Prompts for task ID
        - Validates ID is a positive integer
        - Prompts for new title (optional)
        - Prompts for new description (optional)
        - Ensures at least one field is provided
        - Calls services.update_task() with connection
        - Displays success or error message from service layer

    Constitutional Compliance:
        ✅ Input collection and format validation
        ✅ Calls service layer for business logic
        ✅ NO SQL queries
        ✅ NO business validation (delegates to service layer)
    """
    print("\n--- Update Task ---")

    # Collect task ID
    task_id_input = input("Enter task ID to update: ").strip()

    try:
        task_id = int(task_id_input)
        if task_id <= 0:
            print("Error: Task ID must be a positive integer.")
            return
    except ValueError:
        print("Error: Invalid task ID. Please enter a number.")
        return

    # Collect new title (optional)
    print("\nLeave field empty to keep current value:")
    new_title = input("Enter new title (or press Enter to skip): ").strip()

    # If empty, set to None to indicate no change
    if not new_title:
        new_title = None

    # Collect new description (optional)
    new_description = input("Enter new description (or press Enter to skip): ").strip()

    # If empty, set to None to indicate no change
    if not new_description:
        new_description = None

    # Validate at least one field is provided
    if new_title is None and new_description is None:
        print("Error: Must provide at least one field to update (title or description).")
        return

    # Call service layer to update task
    result = services.update_task(conn, task_id, new_title, new_description)

    # Display result from service layer
    if result['success']:
        print(f"\n✓ {result['message']}")
    else:
        print(f"\n✗ {result['message']}")


def handle_toggle_task(conn) -> None:
    """
    Collect task ID and toggle completion via service layer.

    Args:
        conn: Active database connection to pass to service layer

    Implementation Notes:
        - Prompts for task ID
        - Validates ID is a positive integer
        - Calls services.toggle_task_completion() with connection
        - Displays success or error message from service layer

    Constitutional Compliance:
        ✅ Input collection and format validation
        ✅ Calls service layer for business logic
        ✅ NO SQL queries
        ✅ NO business logic
    """
    print("\n--- Toggle Task Completion ---")

    # Collect task ID
    task_id_input = input("Enter task ID to toggle: ").strip()

    try:
        task_id = int(task_id_input)
        if task_id <= 0:
            print("Error: Task ID must be a positive integer.")
            return
    except ValueError:
        print("Error: Invalid task ID. Please enter a number.")
        return

    # Call service layer to toggle task completion
    result = services.toggle_task_completion(conn, task_id)

    # Display result from service layer
    if result['success']:
        print(f"\n✓ {result['message']}")
    else:
        print(f"\n✗ {result['message']}")


def handle_delete_task(conn) -> None:
    """
    Collect task ID and delete task via service layer.

    Args:
        conn: Active database connection to pass to service layer

    Implementation Notes:
        - Prompts for task ID
        - Validates ID is a positive integer
        - Prompts for confirmation (destructive action)
        - Calls services.delete_task() with connection
        - Displays success or error message from service layer

    Constitutional Compliance:
        ✅ Input collection and format validation
        ✅ Confirmation prompt for destructive action
        ✅ Calls service layer for business logic
        ✅ NO SQL queries
        ✅ NO business logic
    """
    print("\n--- Delete Task ---")

    # Collect task ID
    task_id_input = input("Enter task ID to delete: ").strip()

    try:
        task_id = int(task_id_input)
        if task_id <= 0:
            print("Error: Task ID must be a positive integer.")
            return
    except ValueError:
        print("Error: Invalid task ID. Please enter a number.")
        return

    # Confirmation prompt for destructive action
    confirmation = input(f"Are you sure you want to delete task #{task_id}? (yes/no): ").strip().lower()

    if confirmation not in ['yes', 'y']:
        print("Deletion cancelled.")
        return

    # Call service layer to delete task
    result = services.delete_task(conn, task_id)

    # Display result from service layer
    if result['success']:
        print(f"\n✓ {result['message']}")
    else:
        print(f"\n✗ {result['message']}")
