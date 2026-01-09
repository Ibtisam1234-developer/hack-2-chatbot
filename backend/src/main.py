"""
Application Entry Point for Interactive Todo Application (v2.0.0)

Owner: Menu/UX Agent
Purpose: Entry point for the Typer-based CLI
Architecture: Delegates execution to src/cli.py

Constitutional Constraints:
- ALLOWED: CLI orchestration, startup/shutdown logic
- FORBIDDEN: SQL queries, Business logic, Direct database access
"""

import sys
import asyncio
import selectors
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.panel import Panel
from rich.table import Table
from datetime import datetime

# Set event loop policy for Windows if needed
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from src.cli import add, list_tasks, search, update, delete, complete, history, async_add, async_list_tasks, async_search, async_update, async_delete, async_complete, async_history
from src.models import Priority, TaskStatus, RecurrenceInterval
from src.database import init_db
from src.notification_manager import check_due_tasks_and_notify

console = Console()

def show_welcome():
    """Display welcome message and instructions."""
    console.print(Panel.fit(
        "[bold cyan]Interactive Todo Application (v2.1.0)[/bold cyan]\n"
        "Advanced Intelligent Task Management",
        title="Welcome",
        border_style="cyan"
    ))

async def async_history(task_id: int):
    """Placeholder or delegate to cli implementation."""
    from src.cli import history
    # The history command in cli.py is already async-wrapped
    # But for simplicity, we call the logic directly if available
    from src import services
    from rich.table import Table

    result = await services.get_task_history(task_id)
    if not result["success"]:
        console.print(f"[red]{result['message']}[/red]")
        return

    tasks = result["data"]
    table = Table(title=f"Task History Series: {task_id}", header_style="bold cyan")
    table.add_column("ID", justify="right")
    table.add_column("Status")
    table.add_column("Completed Date")
    table.add_column("Due Date")

    for task in tasks:
        # Convert task to dict if it's a Pydantic model
        t_dict = task.to_dict() if hasattr(task, 'to_dict') else task
        status_icon = "[green]✓[/green]" if t_dict['status'] == TaskStatus.COMPLETED else "[yellow]○[/yellow]"
        completed_str = t_dict['updated_at'].strftime("%Y-%m-%d %H:%M") if t_dict['status'] == TaskStatus.COMPLETED else "-"
        due_str = t_dict['due_date'].strftime("%Y-%m-%d %H:%M") if t_dict['due_date'] else "-"
        table.add_row(str(t_dict['id']), status_icon, completed_str, due_str)

    console.print(table)

async def interactive_loop():
    """Run the application in a highly interactive continuous loop."""
    show_welcome()

    while True:
        console.print("\n[bold]Main Menu:[/bold]")
        console.print("1. [green]Add[/green] a new task (Interactive Wizard)")
        console.print("2. [blue]List[/blue] all tasks")
        console.print("3. [yellow]Search[/yellow] tasks")
        console.print("4. [magenta]Update[/magenta] a task")
        console.print("5. [cyan]Complete/Toggle[/cyan] a task")
        console.print("6. [white]View History[/white] of a recurring task")
        console.print("7. [red]Delete[/red] a task")
        console.print("0. [grey50]Exit[/grey50]")

        choice = Prompt.ask("\nChoose an action", choices=["1", "2", "3", "4", "5", "6", "7", "0"], default="2")

        try:
            if choice == "1": # Add
                await async_add(title="", interactive=True)

            elif choice == "2": # List
                status_raw = Prompt.ask("Filter by status", choices=["pending", "completed", "all"], default="all")
                prio_raw = Prompt.ask("Filter by priority", choices=["low", "medium", "high", "all"], default="all")
                sort = Prompt.ask("Sort by", choices=["date", "priority", "alpha"], default="date")

                status_filter = None
                if status_raw != "all":
                    status_filter = TaskStatus(status_raw)

                prio_filter = None
                if prio_raw != "all":
                    prio_filter = Priority(prio_raw)

                await async_list_tasks(
                    status=status_filter,
                    priority=prio_filter,
                    sort=sort
                )

            elif choice == "3": # Search
                query = Prompt.ask("Enter search keyword")
                await async_search(query=query)

            elif choice == "4": # Update
                task_id = IntPrompt.ask("Enter Task ID to update")
                await async_update(task_id=task_id, interactive=True)

            elif choice == "5": # Complete
                task_id = IntPrompt.ask("Enter Task ID to toggle")
                await async_complete(task_id=task_id)

            elif choice == "6": # History
                task_id = IntPrompt.ask("Enter the original Task ID")
                await async_history(task_id=task_id)

            elif choice == "7": # Delete
                task_id = IntPrompt.ask("Enter Task ID to delete")
                await async_delete(task_id=task_id)

            elif choice == "0": # Exit
                console.print("[cyan]Goodbye![/cyan]")
                break

        except Exception as e:
            console.print(f"[bold red]An error occurred:[/bold red] {e}")

async def main():
    """Execute the application. Always enters the primary interactive loop."""
    # Ensure database is initialized before any operations
    try:
        await init_db()
    except Exception as e:
        console.print(f"[bold red]Critical Error during database initialization:[/bold red] {e}")
        sys.exit(1)

    # Boot check: Notifications for due tasks
    try:
        notified_count = await check_due_tasks_and_notify()
        if notified_count > 0:
            console.print(f"[bold yellow]Reminder:[/bold yellow] You have {notified_count} tasks due soon! (Check OS notifications)")
    except Exception as e:
        # Catch silently as per constraints
        pass

    try:
        await interactive_loop()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Application interrupted. Exiting...[/yellow]")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
