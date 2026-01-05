"""Display utilities for CLI output.

This module provides rich-based display functions for CLI output.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scan2mesh.models import CapturePlan, ProjectConfig


console = Console()


def display_init_result(config: ProjectConfig, project_dir: str) -> None:
    """Display project initialization result.

    Args:
        config: The created project configuration
        project_dir: Path to the project directory
    """
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Project Directory", project_dir)
    table.add_row("Object Name", config.object_name)
    table.add_row("Class ID", str(config.class_id))
    table.add_row("Tags", ", ".join(config.tags) if config.tags else "-")
    scale_method = config.scale_info.method if config.scale_info else "-"
    table.add_row("Scale Method", scale_method)
    table.add_row("Config Hash", config.config_hash[:16] + "...")

    panel = Panel(
        table,
        title="[bold green]Project Initialized Successfully[/bold green]",
        border_style="green",
    )
    console.print(panel)


def display_error(message: str, exception: Exception | None = None) -> None:
    """Display an error message.

    Args:
        message: The error message to display
        exception: Optional exception for additional context
    """
    error_text = f"[bold red]Error:[/bold red] {message}"
    if exception:
        error_text += f"\n[dim]{type(exception).__name__}: {exception}[/dim]"

    console.print(Panel(error_text, border_style="red"))


def display_success(message: str) -> None:
    """Display a success message.

    Args:
        message: The success message to display
    """
    console.print(f"[bold green]✓[/bold green] {message}")


def display_warning(message: str) -> None:
    """Display a warning message.

    Args:
        message: The warning message to display
    """
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def display_info(message: str) -> None:
    """Display an info message.

    Args:
        message: The info message to display
    """
    console.print(f"[bold blue]i[/bold blue] {message}")


def display_not_implemented(stage_name: str) -> None:
    """Display a not implemented message.

    Args:
        stage_name: Name of the unimplemented stage
    """
    console.print(
        Panel(
            f"[yellow]Stage '[bold]{stage_name}[/bold]' is not yet implemented.[/yellow]",
            border_style="yellow",
        )
    )


def display_plan_result(plan: CapturePlan, project_dir: str) -> None:
    """Display capture plan generation result.

    Args:
        plan: The created capture plan
        project_dir: Path to the project directory
    """
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Project Directory", project_dir)
    table.add_row("Preset", plan.preset.value)
    table.add_row("Total Viewpoints", str(len(plan.viewpoints)))
    table.add_row("Min Required Frames", str(plan.min_required_frames))
    table.add_row("Recommended Distance", f"{plan.recommended_distance_m} m")

    panel = Panel(
        table,
        title="[bold green]Capture Plan Generated Successfully[/bold green]",
        border_style="green",
    )
    console.print(panel)

    if plan.notes:
        console.print()
        console.print("[bold cyan]Notes:[/bold cyan]")
        for note in plan.notes:
            console.print(f"  [dim]-[/dim] {note}")
