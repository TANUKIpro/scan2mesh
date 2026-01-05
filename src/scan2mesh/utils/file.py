"""File operation utilities."""

import json
from pathlib import Path
from typing import Any

from scan2mesh.exceptions import StorageError


def save_json_atomic(path: Path, data: dict[str, Any]) -> None:
    """Save data to JSON file atomically.

    Uses a temporary file and rename to ensure atomic write,
    preventing data corruption if the process is interrupted.

    Args:
        path: Target file path
        data: Data to save as JSON

    Raises:
        StorageError: If the write operation fails
    """
    temp_path = path.with_suffix(".tmp")

    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        # Atomic rename
        temp_path.rename(path)
    except OSError as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        raise StorageError(f"Failed to save JSON to {path}: {e}") from e


def load_json(path: Path) -> dict[str, Any]:
    """Load data from JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON data as dictionary

    Raises:
        StorageError: If the file cannot be read or parsed
    """
    try:
        with path.open(encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data
    except FileNotFoundError as e:
        raise StorageError(f"File not found: {path}") from e
    except json.JSONDecodeError as e:
        raise StorageError(f"Invalid JSON in {path}: {e}") from e
    except OSError as e:
        raise StorageError(f"Failed to read {path}: {e}") from e
