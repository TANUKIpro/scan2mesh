"""Application configuration management."""

import json
from pathlib import Path

from scan2mesh_gui.models.config import AppConfig


# Default paths
DEFAULT_BASE_DIR = Path.cwd()
DEFAULT_CONFIG_FILE = "config/app_config.json"


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or DEFAULT_BASE_DIR
        self.config_path = self.base_dir / DEFAULT_CONFIG_FILE
        self._config: AppConfig | None = None

    @property
    def config(self) -> AppConfig:
        """Get the current configuration, loading if necessary."""
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> AppConfig:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    data = json.load(f)
                return AppConfig(**data)
            except (json.JSONDecodeError, ValueError):
                # Fall back to defaults on error
                pass
        return AppConfig()

    def save(self) -> None:
        """Save current configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.config_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self.config.model_dump(), f, indent=2)
        temp_path.rename(self.config_path)

    def update(self, **kwargs: object) -> AppConfig:
        """Update configuration with new values."""
        data = self.config.model_dump()
        for key, value in kwargs.items():
            if hasattr(self.config, key) and value is not None:
                data[key] = value
        self._config = AppConfig(**data)
        self.save()
        return self._config

    @property
    def profiles_dir(self) -> Path:
        """Get the profiles directory path."""
        return self.base_dir / self.config.profiles_dir

    @property
    def projects_dir(self) -> Path:
        """Get the projects directory path."""
        return self.base_dir / self.config.projects_dir

    @property
    def output_dir(self) -> Path:
        """Get the output directory path."""
        return self.base_dir / self.config.output_dir


# Global config manager instance
_config_manager: ConfigManager | None = None


def get_config_manager(base_dir: Path | None = None) -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None or (base_dir and _config_manager.base_dir != base_dir):
        _config_manager = ConfigManager(base_dir)
    return _config_manager


def get_config() -> AppConfig:
    """Get the current application configuration."""
    return get_config_manager().config
