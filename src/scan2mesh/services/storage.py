"""Storage service for project data management."""

from pathlib import Path

from scan2mesh.exceptions import ConfigError, StorageError
from scan2mesh.models import ProjectConfig
from scan2mesh.utils import load_json, save_json_atomic


class StorageService:
    """Service for managing project storage.

    Handles all file I/O operations for project data including
    configuration files, frames, and metrics.

    Attributes:
        project_dir: Path to the project directory
    """

    PROJECT_CONFIG_FILE = "project.json"
    CAPTURE_PLAN_FILE = "capture_plan.json"
    FRAMES_METADATA_FILE = "frames_metadata.json"

    def __init__(self, project_dir: Path) -> None:
        """Initialize StorageService.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir

    @property
    def config_path(self) -> Path:
        """Path to project configuration file."""
        return self.project_dir / self.PROJECT_CONFIG_FILE

    @property
    def capture_plan_path(self) -> Path:
        """Path to capture plan file."""
        return self.project_dir / self.CAPTURE_PLAN_FILE

    def save_project_config(self, config: ProjectConfig) -> None:
        """Save project configuration to file.

        Args:
            config: ProjectConfig instance to save

        Raises:
            StorageError: If the save operation fails
        """
        data = config.model_dump(mode="json")
        save_json_atomic(self.config_path, data)

    def load_project_config(self) -> ProjectConfig:
        """Load project configuration from file.

        Returns:
            ProjectConfig instance

        Raises:
            ConfigError: If the configuration file is missing or invalid
        """
        if not self.config_path.exists():
            raise ConfigError(f"Project config not found: {self.config_path}")

        try:
            data = load_json(self.config_path)
            return ProjectConfig.model_validate(data)
        except StorageError:
            raise
        except Exception as e:
            raise ConfigError(f"Invalid project config: {e}") from e

    def project_exists(self) -> bool:
        """Check if a project exists at this location.

        Returns:
            True if project.json exists, False otherwise
        """
        return self.config_path.exists()

    def get_subdirectory(self, name: str) -> Path:
        """Get path to a project subdirectory.

        Args:
            name: Subdirectory name (e.g., 'raw_frames', 'asset')

        Returns:
            Path to the subdirectory
        """
        return self.project_dir / name

    def ensure_subdirectory(self, name: str) -> Path:
        """Ensure a subdirectory exists, creating it if necessary.

        Args:
            name: Subdirectory name

        Returns:
            Path to the subdirectory

        Raises:
            StorageError: If the directory cannot be created
        """
        path = self.get_subdirectory(name)
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError as e:
            raise StorageError(f"Failed to create directory {path}: {e}") from e
