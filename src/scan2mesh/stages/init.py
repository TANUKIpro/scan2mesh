"""Project initialization stage.

This module provides the ProjectInitializer class for creating new scan2mesh projects.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from scan2mesh.models import OutputPreset, ProjectConfig, ScaleInfo
from scan2mesh.services import StorageService
from scan2mesh.utils import calculate_config_hash


logger = logging.getLogger("scan2mesh.stages.init")


class ProjectInitializer:
    """Initialize new scan2mesh projects.

    This stage handles:
    - Creating project directory structure
    - Generating project configuration
    - Saving initial project.json

    Attributes:
        project_dir: Path to the project directory
        storage: StorageService instance
    """

    REQUIRED_DIRS: ClassVar[list[str]] = [
        "raw_frames",
        "keyframes",
        "masked_frames",
        "recon",
        "asset",
        "metrics",
        "logs",
    ]

    def __init__(self, project_dir: Path) -> None:
        """Initialize ProjectInitializer.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir
        self.storage = StorageService(project_dir)

    def initialize(
        self,
        object_name: str,
        class_id: int,
        preset: OutputPreset | None = None,
        tags: list[str] | None = None,
        known_dimension_mm: float | None = None,
        dimension_type: str | None = None,
    ) -> ProjectConfig:
        """Initialize a new project.

        Creates the project directory structure and saves the initial configuration.

        Args:
            object_name: Name of the object to scan
            class_id: Class ID for the object (0-9999)
            preset: Output preset configuration (optional)
            tags: List of tags for categorization (optional)
            known_dimension_mm: Known dimension in millimeters (optional)
            dimension_type: Type of known dimension (optional)

        Returns:
            ProjectConfig instance with the created configuration

        Raises:
            FileExistsError: If the project directory already exists
            ValueError: If the object name is invalid
        """
        logger.info(f"Initializing project: {object_name} (class_id={class_id})")

        # Check if project already exists
        if self.project_dir.exists():
            raise FileExistsError(
                f"Project directory already exists: {self.project_dir}"
            )

        # Create directory structure
        self._create_directory_structure()
        logger.debug(f"Created directory structure at {self.project_dir}")

        # Build scale info
        scale_info = self._build_scale_info(known_dimension_mm, dimension_type)

        # Build configuration
        now = datetime.now()
        config_data = {
            "object_name": object_name,
            "class_id": class_id,
            "tags": tags or [],
            "output_preset": preset or OutputPreset(),
            "scale_info": scale_info,
            "created_at": now,
            "updated_at": now,
        }

        # Calculate config hash
        config_hash = calculate_config_hash(config_data)

        # Create config object
        config = ProjectConfig(**config_data, config_hash=config_hash)

        # Save configuration
        self.storage.save_project_config(config)
        logger.info(f"Project initialized successfully: {self.project_dir}")

        return config

    def load_config(self) -> ProjectConfig:
        """Load existing project configuration.

        Returns:
            ProjectConfig instance

        Raises:
            ConfigError: If the configuration file is missing or invalid
        """
        return self.storage.load_project_config()

    def save_config(self, config: ProjectConfig) -> None:
        """Save project configuration.

        Updates the updated_at timestamp before saving.

        Args:
            config: ProjectConfig instance to save
        """
        # Update timestamp
        updated_config = ProjectConfig(
            schema_version=config.schema_version,
            object_name=config.object_name,
            class_id=config.class_id,
            tags=config.tags,
            output_preset=config.output_preset,
            scale_info=config.scale_info,
            created_at=config.created_at,
            updated_at=datetime.now(),
            config_hash=config.config_hash,
        )
        self.storage.save_project_config(updated_config)

    def _create_directory_structure(self) -> None:
        """Create the project directory structure.

        Creates the main project directory and all required subdirectories.

        Raises:
            OSError: If directory creation fails
        """
        # Create main directory with restricted permissions
        self.project_dir.mkdir(parents=True, exist_ok=False, mode=0o700)

        # Create subdirectories
        for dir_name in self.REQUIRED_DIRS:
            subdir = self.project_dir / dir_name
            subdir.mkdir(mode=0o700)

    def _build_scale_info(
        self,
        known_dimension_mm: float | None,
        dimension_type: str | None,
    ) -> ScaleInfo:
        """Build scale information based on provided parameters.

        Args:
            known_dimension_mm: Known dimension in millimeters (optional)
            dimension_type: Type of known dimension (optional)

        Returns:
            ScaleInfo instance
        """
        if known_dimension_mm is not None:
            return ScaleInfo(
                method="known_dimension",
                known_dimension_mm=known_dimension_mm,
                dimension_type=dimension_type,
                uncertainty="low",
            )

        return ScaleInfo(
            method="realsense_depth_scale",
            uncertainty="medium",
        )
