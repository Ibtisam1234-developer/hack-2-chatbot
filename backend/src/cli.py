"""
CLI Layer for Interactive Todo Application (v2.0.0)

Owner: Menu/UX Agent
Purpose: Interactive terminal interface using Typer and Rich
Architecture: Command-driven CLI with async service orchestration

Constitutional Constraints:
- ALLOWED: Rich UI output, Typer commands, User input collection, Service layer orchestration
- FORBIDDEN: SQL queries, Direct database access, Business logic validation (delegates to services)
"""

import asyncio
import typer
import questionary
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum

from src.models import Priority, TaskStatus, TaskCreate, TaskUpdate, RecurrenceInterval
from src import services

# Initialize Typer app and Rich console
app = typer.Typer(help="Interactive Todo Application CLI")
console = Console()

class SortOption(str, Enum):
    DATE = "date"
    ALPHA = "alpha"
    PRIORITY = "priority"

def get_priority_color(priority: Any) -> str:
    """Return color associated with priority level."""
    # Handle both Enum and raw string
    val = priority.value if hasattr(priority, 'value') else str(priority)
    colors = {
        "high": "red",
        "medium": "yellow",
        "low": "green"
    }
    return colors.get(val.lower(), "white")

def display_error(message: str):
    """Display error message in a Rich panel."""
    console.print(Panel(f"[bold red]Error:[/bold red] {message}", border_style="red"))

def display_success(message: str):
    """Display success message."""
    console.print(f"[bold green]✓[/bold green] {message}")

async def run_with_progress(coro, description: str):
    """Run an async coroutine with a Rich progress spinner."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=description, total=None)
        return await coro

async def interactive_date_picker(prompt: str) -> Optional[datetime]:
    """Helper to pick a date using natural language or interactive prompt."""
    date_str = await asyncio.to_thread(questionary.text(f"{prompt} (e.g. 'tomorrow', 'next mon at 3pm')").ask)
    if not date_str:
        return None

    parsed_date = services.parse_natural_date(date_str)
    if not parsed_date:
        console.print("[yellow]Could not parse date. Please use YYYY-MM-DD format or try again.[/yellow]")
        # Fallback to manual entry
        manual_str = await asyncio.to_thread(questionary.text("Due Date (YYYY-MM-DD HH:MM:SS)").ask)
        if not manual_str: return None
        try:
            return datetime.fromisoformat(manual_str.replace(' ', 'T'))
        except ValueError:
            console.print("[red]Invalid date format.[/red]")
            return None
    return parsed_date

@app.command()
def add(
    title: Optional[str] = typer.Argument(None, help="The title of the task"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Task description"),
    priority: Priority = typer.Option(Priority.MEDIUM, "--priority", "-p", help="Task priority"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Task category"),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (natural language)"),
    recurrence: RecurrenceInterval = typer.Option(RecurrenceInterval.NONE, "--recurrence", "-r", help="Recurrence interval"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Use interactive wizard"),
):
    """Add a new task with optional metadata."""
    async def _add():
        nonlocal title, description, priority, category, due, recurrence

        if interactive or not title:
            # Use questionary for interactive form
            title = await asyncio.to_thread(questionary.text("Task title:", validate=lambda text: len(text) > 0).ask)
            description = await asyncio.to_thread(questionary.text("Description (optional):").ask)
            choice = await asyncio.to_thread(questionary.select(
                "Priority:",
                choices=["low", "medium", "high"],
                default=priority.value if priority else "medium"
            ).ask)
            priority = Priority(choice)
            category = await asyncio.to_thread(questionary.text("Category (optional):").ask)

            # Date picking
            due_date = await interactive_date_picker("Due Date")

            # Recurrence
            choice = await asyncio.to_thread(questionary.select(
                "Recurrence:",
                choices=["none", "daily", "weekly", "monthly"],
                default=recurrence.value if recurrence else "none"
            ).ask)
            recurrence = RecurrenceInterval(choice)
        else:
            # Command line mode
            due_date = services.parse_natural_date(due) if due else None

        task_data = TaskCreate(
            title=title,
            description=description,
            priority=priority,
            category=category,
            due_date=due_date,
            recurrence_interval=recurrence
        )
        result = await run_with_progress(services.create_task(task_data), "Creating task...")

        if result["success"]:
            display_success(result["message"])
        else:
            display_error(result["message"])

    asyncio.run(_add())

async def async_add(title: str = "", description: Optional[str] = None, priority: Priority = Priority.MEDIUM,
                    category: Optional[str] = None, due: Optional[str] = None,
                    recurrence: RecurrenceInterval = RecurrenceInterval.NONE,
                    interactive: bool = False):
    """Async version of add for interactive mode."""
    if interactive or not title:
        # Use questionary for interactive form
        title = await asyncio.to_thread(questionary.text("Task title:", validate=lambda text: len(text) > 0).ask)
        description = await asyncio.to_thread(questionary.text("Description (optional):").ask)
        choice = await asyncio.to_thread(questionary.select(
            "Priority:",
            choices=["low", "medium", "high"],
            default=priority.value if priority else "medium"
        ).ask)
        priority = Priority(choice)
        category = await asyncio.to_thread(questionary.text("Category (optional):").ask)

        # Date picking
        due_date = await interactive_date_picker("Due Date")

        # Recurrence
        choice = await asyncio.to_thread(questionary.select(
            "Recurrence:",
            choices=["none", "daily", "weekly", "monthly"],
            default=recurrence.value if recurrence else "none"
        ).ask)
        recurrence = RecurrenceInterval(choice)
    else:
        # Command line mode
        due_date = services.parse_natural_date(due) if due else None

    task_data = TaskCreate(
        title=title,
        description=description,
        priority=priority,
        category=category,
        due_date=due_date,
        recurrence_interval=recurrence
    )
    result = await run_with_progress(services.create_task(task_data), "Creating task...")

    if result["success"]:
        display_success(result["message"])
    else:
        display_error(result["message"])

async def async_list_tasks(status: Optional[TaskStatus] = None, category: Optional[str] = None,
                           priority: Optional[Priority] = None, sort: str = "date"):
    """Async version of list_tasks for interactive mode."""
    sort_enum = SortOption(sort) if sort in ["date", "alpha", "priority"] else SortOption.DATE

    result = await run_with_progress(
        services.get_tasks(status=status, category=category, priority=priority, sort_by=sort_enum.value),
        "Fetching tasks..."
    )

    if not result["success"]:
        display_error(result["message"])
        return

    tasks = result["data"]
    if not tasks:
        console.print("[yellow]No tasks found matching criteria.[/yellow]")
        return

    table = Table(title="Todo Tasks", header_style="bold cyan")
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Priority", justify="center")
    table.add_column("Title", style="white")
    table.add_column("Category", style="blue")
    table.add_column("Due Date", style="green")
    table.add_column("Recur", style="yellow")

    for task in tasks:
        # Normalize status to icon
        task_status = task.status.value if hasattr(task.status, 'value') else str(task.status)
        status_icon = "[green]✓[/green]" if task_status == "completed" else "[yellow]○[/yellow]"

        # Normalize priority and recurrence
        p_val = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
        r_val = task.recurrence_interval.value if hasattr(task.recurrence_interval, 'value') else str(task.recurrence_interval)

        p_color = get_priority_color(p_val)
        priority_str = f"[{p_color}]{p_val.upper()}[/{p_color}]"
        due_str = task.due_date.strftime("%Y-%m-%d %H:%M") if task.due_date else "-"
        recur_str = r_val if r_val != "none" else "-"

        table.add_row(
            str(task.id),
            status_icon,
            priority_str,
            task.title,
            task.category or "-",
            due_str,
            recur_str
        )

    console.print(table)
    console.print(f"\n[italic]{result['message']}[/italic]")

async def async_search(query: str):
    """Async version of search for interactive mode."""
    result = await run_with_progress(services.search_tasks(query), f"Searching for '{query}'...")

    if not result["success"]:
        display_error(result["message"])
        return

    tasks = result["data"]
    if not tasks:
        console.print(f"[yellow]No tasks found matching '{query}'.[/yellow]")
        return

    table = Table(title=f"Search Results: {query}")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Title", style="magenta")

    for task in tasks:
        status_icon = "✓" if task.status == TaskStatus.COMPLETED else "○"
        table.add_row(str(task.id), status_icon, task.title)

    console.print(table)

async def async_update(task_id: int, title: Optional[str] = None, description: Optional[str] = None,
                      priority: Optional[Priority] = None, category: Optional[str] = None,
                      due: Optional[str] = None, status: Optional[TaskStatus] = None,
                      recurrence: Optional[RecurrenceInterval] = None,
                      interactive: bool = False):
    """Async version of update for interactive mode."""
    if interactive:
        # Fetch existing task first
        res = await services.get_tasks()
        existing = None
        for t in res["data"]:
            if t.id == task_id:
                existing = t
                break

        if existing:
            title = await asyncio.to_thread(questionary.text("New title:", default=existing.title).ask)
            choice = await asyncio.to_thread(questionary.select(
                "New Priority:",
                choices=["low", "medium", "high"],
                default=existing.priority if existing.priority else "medium"
            ).ask)
            priority = Priority(choice)
            due_date = await interactive_date_picker("New Due Date")
            choice = await asyncio.to_thread(questionary.select(
                "New Recurrence:",
                choices=["none", "daily", "weekly", "monthly"],
                default=existing.recurrence_interval if existing.recurrence_interval else "none"
            ).ask)
            recurrence = RecurrenceInterval(choice)
        else:
            display_error(f"Task {task_id} not found.")
            return
    else:
        # Command line mode
        due_date = services.parse_natural_date(due) if due else None

    # Handle completion status specifically for boolean transition
    is_completed = None
    if status:
        is_completed = (status == TaskStatus.COMPLETED)

    update_data = TaskUpdate(
        title=title,
        description=description,
        priority=priority,
        category=category,
        due_date=due_date,
        is_completed=is_completed,
        recurrence_interval=recurrence
    )

    result = await run_with_progress(services.update_task(task_id, update_data), f"Updating task {task_id}...")

    if result["success"]:
        display_success(result["message"])
    else:
        display_error(result["message"])

async def async_delete(task_id: int, force: bool = True):
    """Async version of delete for interactive mode."""
    result = await run_with_progress(services.delete_task(task_id), f"Deleting task {task_id}...")

    if result["success"]:
        display_success(result["message"])
    else:
        display_error(result["message"])

async def async_complete(task_id: int):
    """Async version of complete for interactive mode."""
    result = await run_with_progress(services.toggle_task_completion(task_id), f"Toggling status for task {task_id}...")

    if result["success"]:
        display_success(result["message"])
    else:
        display_error(result["message"])

async def async_history(root_task_id: int):
    """Async version of history for interactive mode."""
    result = await run_with_progress(services.get_task_history(root_task_id), f"Fetching history for {root_task_id}...")

    if not result["success"]:
        display_error(result["message"])
        return

    tasks = result["data"]
    table = Table(title=f"Task History Series: {root_task_id}", header_style="bold cyan")
    table.add_column("ID", justify="right")
    table.add_column("Status")
    table.add_column("Completed Date")
    table.add_column("Due Date")

    for task in tasks:
        status_icon = "✓" if task.status == TaskStatus.COMPLETED else "○"
        completed_str = task.updated_at.strftime("%Y-%m-%d %H:%M") if task.status == TaskStatus.COMPLETED else "-"
        due_str = task.due_date.strftime("%Y-%m-%d %H:%M") if task.due_date else "-"
        table.add_row(str(task.id), status_icon, completed_str, due_str)

    console.print(table)

@app.command(name="list")
def list_tasks(
    status: Optional[TaskStatus] = typer.Option(None, "--status", help="Filter by status"),
    category: Optional[str] = typer.Option(None, "--category", help="Filter by category"),
    priority: Optional[Priority] = typer.Option(None, "--priority", help="Filter by priority"),
    sort: SortOption = typer.Option(SortOption.DATE, "--sort", help="Sort order"),
):
    """List tasks with optional filtering and sorting."""
    async def _list():
        await async_list_tasks(status=status, category=category, priority=priority, sort=sort.value)

    asyncio.run(_list())

@app.command()
def search(
    query: str = typer.Argument(..., help="Search keyword"),
):
    """Search for tasks by title or description."""
    async def _search():
        await async_search(query)

    asyncio.run(_search())

@app.command()
def update(
    task_id: int = typer.Argument(..., help="ID of the task to update"),
    title: Optional[str] = typer.Option(None, "--title", help="New title"),
    description: Optional[str] = typer.Option(None, "--desc", help="New description"),
    priority: Optional[Priority] = typer.Option(None, "--priority", help="New priority"),
    category: Optional[str] = typer.Option(None, "--category", help="New category"),
    due: Optional[str] = typer.Option(None, "--due", help="New due date (natural language)"),
    status: Optional[TaskStatus] = typer.Option(None, "--status", help="New status"),
    recurrence: Optional[RecurrenceInterval] = typer.Option(None, "--recurrence", help="New recurrence interval"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Use interactive wizard"),
):
    """Update task metadata."""
    async def _update():
        nonlocal title, description, priority, category, due, status, recurrence

        if interactive:
            # Fetch existing task first
            res = await services.get_tasks() # Inefficient but simple for now
            existing = None
            for t in res["data"]:
                if t.id == task_id:
                    existing = t
                    break

            if existing:
                title = await asyncio.to_thread(questionary.text("New title:", default=existing.title).ask)
                priority = Priority(await asyncio.to_thread(questionary.select("Priority:", choices=["low", "medium", "high"], default=existing.priority).ask))
                due_date = await interactive_date_picker("New Due Date")
                recurrence = RecurrenceInterval(await asyncio.to_thread(questionary.select("Recurrence:", choices=["none", "daily", "weekly", "monthly"], default=existing.recurrence_interval).ask))
            else:
                display_error(f"Task {task_id} not found.")
                return
        else:
            due_date = services.parse_natural_date(due) if due else None

        # Convert status to bool for repository
        is_completed = None
        if status:
            is_completed = (status == TaskStatus.COMPLETED)

        update_data = TaskUpdate(
            title=title,
            description=description,
            priority=priority,
            category=category,
            due_date=due_date,
            is_completed=is_completed,
            recurrence_interval=recurrence
        )

        result = await run_with_progress(services.update_task(task_id, update_data), f"Updating task {task_id}...")

        if result["success"]:
            display_success(result["message"])
        else:
            display_error(result["message"])

    asyncio.run(_update())

@app.command()
def delete(
    task_id: int = typer.Argument(..., help="ID of the task to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a task."""
    async def _delete():
        await async_delete(task_id, force)

    asyncio.run(_delete())

@app.command()
def complete(
    task_id: int = typer.Argument(..., help="ID of the task to toggle completion"),
):
    """Toggle task completion status."""
    async def _toggle():
        await async_complete(task_id)

    asyncio.run(_toggle())

@app.command()
def history(
    root_task_id: int = typer.Argument(..., help="ID of the original task"),
):
    """View history of a recurring task series."""
    async def _history():
        result = await run_with_progress(services.get_task_history(root_task_id), f"Fetching history for {root_task_id}...")

        if not result["success"]:
            display_error(result["message"])
            return

        tasks = result["data"]
        table = Table(title=f"Task History Series: {root_task_id}", header_style="bold cyan")
        table.add_column("ID", justify="right")
        table.add_column("Status")
        table.add_column("Completed Date")
        table.add_column("Due Date")

        for task in tasks:
            status_icon = "✓" if task.status == TaskStatus.COMPLETED else "○"
            completed_str = task.updated_at.strftime("%Y-%m-%d %H:%M") if task.status == TaskStatus.COMPLETED else "-"
            due_str = task.due_date.strftime("%Y-%m-%d %H:%M") if task.due_date else "-"
            table.add_row(str(task.id), status_icon, completed_str, due_str)

        console.print(table)

    asyncio.run(_history())

if __name__ == "__main__":
    app()

