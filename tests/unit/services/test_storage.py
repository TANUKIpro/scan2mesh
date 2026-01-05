"""Tests for scan2mesh.services.storage module."""

from datetime import datetime
from pathlib import Path

import pytest

from scan2mesh.exceptions import ConfigError
from scan2mesh.models import ProjectConfig
from scan2mesh.services.storage import StorageService


class TestStorageService:
    """Tests for StorageService class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test StorageService initialization."""
        service = StorageService(tmp_path)
        assert service.project_dir == tmp_path

    def test_config_path(self, tmp_path: Path) -> None:
        """Test config_path property."""
        service = StorageService(tmp_path)
        assert service.config_path == tmp_path / "project.json"

    def test_project_exists_false(self, tmp_path: Path) -> None:
        """Test project_exists returns False when no config."""
        service = StorageService(tmp_path)
        assert service.project_exists() is False

    def test_project_exists_true(self, tmp_path: Path) -> None:
        """Test project_exists returns True when config exists."""
        service = StorageService(tmp_path)
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "project.json").write_text("{}")
        assert service.project_exists() is True


class TestSaveProjectConfig:
    """Tests for save_project_config method."""

    def test_save_config(self, tmp_path: Path) -> None:
        """Test saving project configuration."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        now = datetime.now()
        config = ProjectConfig(
            object_name="test_ball",
            class_id=42,
            config_hash="abc123",
            created_at=now,
            updated_at=now,
        )

        service.save_project_config(config)

        assert service.config_path.exists()
        content = service.config_path.read_text()
        assert "test_ball" in content
        assert "42" in content


class TestLoadProjectConfig:
    """Tests for load_project_config method."""

    def test_load_config(self, tmp_path: Path) -> None:
        """Test loading project configuration."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        # Create config file
        config_data = {
            "schema_version": "1.0",
            "object_name": "test_ball",
            "class_id": 42,
            "tags": [],
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
                "method": "realsense_depth_scale",
                "uncertainty": "medium",
            },
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "config_hash": "abc123",
        }

        import json

        service.config_path.write_text(json.dumps(config_data))

        config = service.load_project_config()

        assert config.object_name == "test_ball"
        assert config.class_id == 42

    def test_load_missing_config(self, tmp_path: Path) -> None:
        """Test loading nonexistent configuration raises error."""
        service = StorageService(tmp_path)

        with pytest.raises(ConfigError, match="not found"):
            service.load_project_config()

    def test_load_invalid_config(self, tmp_path: Path) -> None:
        """Test loading invalid configuration raises error."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        # Create invalid config
        service.config_path.write_text('{"invalid": "config"}')

        with pytest.raises(ConfigError, match="Invalid"):
            service.load_project_config()


class TestSubdirectories:
    """Tests for subdirectory methods."""

    def test_get_subdirectory(self, tmp_path: Path) -> None:
        """Test get_subdirectory returns correct path."""
        service = StorageService(tmp_path)
        path = service.get_subdirectory("raw_frames")
        assert path == tmp_path / "raw_frames"

    def test_ensure_subdirectory(self, tmp_path: Path) -> None:
        """Test ensure_subdirectory creates directory."""
        service = StorageService(tmp_path)
        path = service.ensure_subdirectory("new_dir")

        assert path.exists()
        assert path.is_dir()

    def test_ensure_subdirectory_existing(self, tmp_path: Path) -> None:
        """Test ensure_subdirectory with existing directory."""
        existing = tmp_path / "existing"
        existing.mkdir()

        service = StorageService(tmp_path)
        path = service.ensure_subdirectory("existing")

        assert path.exists()
        assert path == existing
