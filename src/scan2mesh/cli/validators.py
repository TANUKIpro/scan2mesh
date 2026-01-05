"""CLI argument validators.

This module provides validation functions for CLI arguments.
"""

import re
from pathlib import Path

import typer


def validate_object_name(name: str) -> str:
    """Validate object name format.

    Args:
        name: Object name to validate

    Returns:
        The validated name

    Raises:
        typer.BadParameter: If the name is invalid
    """
    if not name:
        raise typer.BadParameter("Object name cannot be empty")

    if len(name) > 100:
        raise typer.BadParameter("Object name must be 100 characters or less")

    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise typer.BadParameter(
            "Object name can only contain letters, numbers, underscores, and hyphens"
        )

    # Check for path traversal attempts
    if ".." in name or "/" in name or "\\" in name:
        raise typer.BadParameter("Object name cannot contain path separators")

    return name


def validate_class_id(class_id: int) -> int:
    """Validate class ID range.

    Args:
        class_id: Class ID to validate

    Returns:
        The validated class ID

    Raises:
        typer.BadParameter: If the class ID is out of range
    """
    if class_id < 0 or class_id > 9999:
        raise typer.BadParameter("Class ID must be between 0 and 9999")

    return class_id


def validate_project_dir(project_dir: Path | None) -> Path:
    """Validate and resolve project directory path.

    Args:
        project_dir: Project directory path (optional)

    Returns:
        Resolved project directory path

    Raises:
        typer.BadParameter: If the path is invalid
    """
    if project_dir is None:
        return Path.cwd() / "projects"

    resolved = project_dir.resolve()

    # Ensure we're not writing to system directories
    forbidden_prefixes = ["/bin", "/sbin", "/usr", "/etc", "/var", "/sys", "/proc"]
    for prefix in forbidden_prefixes:
        if str(resolved).startswith(prefix):
            raise typer.BadParameter(f"Cannot create projects in {prefix}")

    return resolved


def validate_dimension(value: float | None) -> float | None:
    """Validate dimension value.

    Args:
        value: Dimension value in millimeters

    Returns:
        The validated value

    Raises:
        typer.BadParameter: If the value is invalid
    """
    if value is None:
        return None

    if value <= 0:
        raise typer.BadParameter("Dimension must be positive")

    if value > 10000:
        raise typer.BadParameter("Dimension must be 10000mm or less")

    return value
