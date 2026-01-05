"""Pytest configuration and fixtures for scan2mesh tests."""

from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory.

    Args:
        tmp_path: Pytest temporary path fixture

    Returns:
        Path to the temporary project directory
    """
    project_dir = tmp_path / "test_project"
    return project_dir


@pytest.fixture
def existing_project_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create an existing project directory structure.

    Args:
        tmp_path: Pytest temporary path fixture

    Yields:
        Path to the existing project directory
    """
    project_dir = tmp_path / "existing_project"
    project_dir.mkdir()

    # Create subdirectories
    subdirs = [
        "raw_frames",
        "keyframes",
        "masked_frames",
        "recon",
        "asset",
        "metrics",
        "logs",
    ]
    for subdir in subdirs:
        (project_dir / subdir).mkdir()

    yield project_dir


@pytest.fixture
def sample_config_data() -> dict:
    """Provide sample configuration data.

    Returns:
        Dictionary with sample configuration values
    """
    return {
        "object_name": "test_object",
        "class_id": 42,
        "tags": ["test", "sample"],
        "output_preset": {
            "coordinate_system": {
                "up_axis": "Z",
                "forward_axis": "X",
                "units": "meters",
            },
            "lod_levels": [100000, 50000, 10000],
            "texture_resolution": 2048,
            "generate_collision": True,
        },
        "scale_info": {
            "method": "known_dimension",
            "known_dimension_mm": 100.0,
            "dimension_type": "width",
            "uncertainty": "low",
        },
    }
