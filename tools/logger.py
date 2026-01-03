from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from typing import Dict, Any, List

console = Console()

class RichLogger:
    def __init__(self):
        self.console = console

    def log_plan(self, plan: Dict[str, Any]):
        """Renders the plan as a tree."""
        tree = Tree(f"[bold green]Plan: {plan.get('task')}[/bold green]")

        for i, step in enumerate(plan.get("steps", [])):
             tree.add(f"[bold cyan]Step {i+1}:[/bold cyan] {step}")

        self.console.print(Panel(tree, title="Execution Plan", expand=False))

    def log_status(self, message: str, spinner_name: str = "dots"):
        """Returns a Live context manager with a spinner. Disables spinner if not in a terminal."""
        if not self.console.is_terminal:
             # Just print the message once and return a no-op context manager
             self.log_info(message)
             from contextlib import nullcontext
             return nullcontext()
        return Live(Spinner(spinner_name, text=message), refresh_per_second=10)

    def log_info(self, message: str):
        self.console.print(f"[blue]INFO[/blue]: {message}")

    def log_warning(self, message: str):
        self.console.print(f"[yellow]WARNING[/yellow]: {message}")

    def log_error(self, message: str):
        self.console.print(f"[red]ERROR[/red]: {message}")

    def log_success(self, message: str):
         self.console.print(f"[green]SUCCESS[/green]: {message}")

rich_logger = RichLogger()
