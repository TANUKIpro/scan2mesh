"""Display utilities for CLI output.

This module provides rich-based display functions for CLI output.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scan2mesh.gates.thresholds import QualityStatus
from scan2mesh.models import (
    CaptureMetrics,
    CapturePlan,
    PreprocessMetrics,
    ProjectConfig,
)


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


def display_capture_result(
    metrics: CaptureMetrics,
    status: QualityStatus,
    project_dir: str,
    suggestions: list[str] | None = None,
) -> None:
    """Display capture result with metrics and quality gate status.

    Args:
        metrics: Capture metrics from the session
        status: Quality gate status
        project_dir: Path to the project directory
        suggestions: Optional list of improvement suggestions
    """
    # Determine panel style based on status
    if status == QualityStatus.PASS:
        title = "[bold green]Capture Completed Successfully[/bold green]"
        border_style = "green"
        status_text = "[green]PASS[/green]"
    elif status == QualityStatus.WARN:
        title = "[bold yellow]Capture Completed with Warnings[/bold yellow]"
        border_style = "yellow"
        status_text = "[yellow]WARN[/yellow]"
    else:
        title = "[bold red]Capture Completed with Issues[/bold red]"
        border_style = "red"
        status_text = "[red]FAIL[/red]"

    # Build metrics table
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Project Directory", project_dir)
    table.add_row("Quality Status", status_text)
    table.add_row("")
    table.add_row("[bold]Frame Statistics[/bold]", "")
    table.add_row("  Total Frames", str(metrics.num_frames_raw))
    table.add_row("  Keyframes", str(metrics.num_keyframes))
    table.add_row("  Duration", f"{metrics.capture_duration_sec:.1f} seconds")
    table.add_row("")
    table.add_row("[bold]Quality Metrics[/bold]", "")
    table.add_row("  Depth Valid Ratio (mean)", f"{metrics.depth_valid_ratio_mean:.1%}")
    table.add_row("  Depth Valid Ratio (min)", f"{metrics.depth_valid_ratio_min:.1%}")
    table.add_row("  Blur Score (mean)", f"{metrics.blur_score_mean:.2f}")
    table.add_row("  Blur Score (min)", f"{metrics.blur_score_min:.2f}")
    table.add_row("  Coverage Score", f"{metrics.coverage_score:.1%}")

    panel = Panel(table, title=title, border_style=border_style)
    console.print(panel)

    # Display suggestions if any
    if suggestions:
        console.print()
        console.print("[bold cyan]Suggestions for Improvement:[/bold cyan]")
        for suggestion in suggestions:
            console.print(f"  [dim]-[/dim] {suggestion}")


def display_preprocess_result(
    metrics: PreprocessMetrics,
    status: QualityStatus,
    project_dir: str,
    suggestions: list[str] | None = None,
) -> None:
    """Display preprocess result with metrics and quality gate status.

    Args:
        metrics: Preprocess metrics from the session
        status: Quality gate status
        project_dir: Path to the project directory
        suggestions: Optional list of improvement suggestions
    """
    # Determine panel style based on status
    if status == QualityStatus.PASS:
        title = "[bold green]Preprocessing Completed Successfully[/bold green]"
        border_style = "green"
        status_text = "[green]PASS[/green]"
    elif status == QualityStatus.WARN:
        title = "[bold yellow]Preprocessing Completed with Warnings[/bold yellow]"
        border_style = "yellow"
        status_text = "[yellow]WARN[/yellow]"
    else:
        title = "[bold red]Preprocessing Completed with Issues[/bold red]"
        border_style = "red"
        status_text = "[red]FAIL[/red]"

    # Build metrics table
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Project Directory", project_dir)
    table.add_row("Quality Status", status_text)
    table.add_row("")
    table.add_row("[bold]Frame Statistics[/bold]", "")
    table.add_row("  Input Keyframes", str(metrics.num_input_frames))
    table.add_row("  Output Frames", str(metrics.num_output_frames))
    table.add_row("  Valid Frames Ratio", f"{metrics.valid_frames_ratio:.1%}")
    table.add_row("")
    table.add_row("[bold]Mask Quality[/bold]", "")
    table.add_row("  Mask Method", metrics.mask_method.value)
    table.add_row("  Mask Area Ratio (mean)", f"{metrics.mask_area_ratio_mean:.1%}")
    table.add_row("  Mask Area Ratio (min)", f"{metrics.mask_area_ratio_min:.1%}")

    panel = Panel(table, title=title, border_style=border_style)
    console.print(panel)

    # Display suggestions if any
    if suggestions:
        console.print()
        console.print("[bold cyan]Suggestions for Improvement:[/bold cyan]")
        for suggestion in suggestions:
            console.print(f"  [dim]-[/dim] {suggestion}")
