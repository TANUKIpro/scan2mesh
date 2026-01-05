"""Tests for scan2mesh.stages.init module."""

from pathlib import Path

import pytest

from scan2mesh.models import OutputPreset, ProjectConfig
from scan2mesh.stages.init import ProjectInitializer


class TestProjectInitializer:
    """Tests for ProjectInitializer class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test ProjectInitializer initialization."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        assert initializer.project_dir == project_dir

    def test_required_dirs(self) -> None:
        """Test required directories list."""
        assert "raw_frames" in ProjectInitializer.REQUIRED_DIRS
        assert "keyframes" in ProjectInitializer.REQUIRED_DIRS
        assert "masked_frames" in ProjectInitializer.REQUIRED_DIRS
        assert "recon" in ProjectInitializer.REQUIRED_DIRS
        assert "asset" in ProjectInitializer.REQUIRED_DIRS
        assert "metrics" in ProjectInitializer.REQUIRED_DIRS
        assert "logs" in ProjectInitializer.REQUIRED_DIRS


class TestInitialize:
    """Tests for initialize method."""

    def test_initialize_basic(self, tmp_path: Path) -> None:
        """Test basic project initialization."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        config = initializer.initialize(
            object_name="test_ball",
            class_id=42,
        )

        assert isinstance(config, ProjectConfig)
        assert config.object_name == "test_ball"
        assert config.class_id == 42
        assert project_dir.exists()

    def test_initialize_with_preset(self, tmp_path: Path) -> None:
        """Test initialization with custom preset."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        preset = OutputPreset(
            lod_triangle_limits=[50000, 25000],
            texture_resolution=1024,
        )

        config = initializer.initialize(
            object_name="test",
            class_id=0,
            preset=preset,
        )

        assert config.output_preset.lod_triangle_limits == [50000, 25000]
        assert config.output_preset.texture_resolution == 1024

    def test_initialize_with_tags(self, tmp_path: Path) -> None:
        """Test initialization with tags."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        config = initializer.initialize(
            object_name="test",
            class_id=0,
            tags=["test", "sample"],
        )

        assert config.tags == ["test", "sample"]

    def test_initialize_with_known_dimension(self, tmp_path: Path) -> None:
        """Test initialization with known dimension."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        config = initializer.initialize(
            object_name="test",
            class_id=0,
            known_dimension_mm=100.0,
            dimension_type="width",
        )

        assert config.scale_info is not None
        assert config.scale_info.method == "known_dimension"
        assert config.scale_info.known_dimension_mm == 100.0
        assert config.scale_info.dimension_type == "width"

    def test_initialize_creates_directories(self, tmp_path: Path) -> None:
        """Test that initialize creates all required directories."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        initializer.initialize(object_name="test", class_id=0)

        for dir_name in ProjectInitializer.REQUIRED_DIRS:
            assert (project_dir / dir_name).exists()
            assert (project_dir / dir_name).is_dir()

    def test_initialize_creates_config_file(self, tmp_path: Path) -> None:
        """Test that initialize creates project.json."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        initializer.initialize(object_name="test", class_id=0)

        config_path = project_dir / "project.json"
        assert config_path.exists()

    def test_initialize_existing_dir_raises(self, tmp_path: Path) -> None:
        """Test that initializing existing project raises error."""
        project_dir = tmp_path / "existing_project"
        project_dir.mkdir()

        initializer = ProjectInitializer(project_dir)

        with pytest.raises(FileExistsError):
            initializer.initialize(object_name="test", class_id=0)

    def test_initialize_config_hash(self, tmp_path: Path) -> None:
        """Test that config hash is generated."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        config = initializer.initialize(object_name="test", class_id=0)

        assert config.config_hash is not None
        assert len(config.config_hash) == 16  # First 16 chars of SHA256


class TestLoadConfig:
    """Tests for load_config method."""

    def test_load_config(self, tmp_path: Path) -> None:
        """Test loading existing config."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        # Initialize first
        original = initializer.initialize(object_name="test", class_id=42)

        # Load config
        loaded = initializer.load_config()

        assert loaded.object_name == original.object_name
        assert loaded.class_id == original.class_id


class TestSaveConfig:
    """Tests for save_config method."""

    def test_save_config_updates_timestamp(self, tmp_path: Path) -> None:
        """Test that save_config updates timestamp."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        # Initialize
        original = initializer.initialize(object_name="test", class_id=0)
        original_updated = original.updated_at

        # Save again
        initializer.save_config(original)

        # Load and check
        loaded = initializer.load_config()
        assert loaded.updated_at >= original_updated


class TestBuildScaleInfo:
    """Tests for _build_scale_info method."""

    def test_build_scale_info_with_dimension(self, tmp_path: Path) -> None:
        """Test building scale info with known dimension."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        scale_info = initializer._build_scale_info(100.0, "width")

        assert scale_info.method == "known_dimension"
        assert scale_info.known_dimension_mm == 100.0
        assert scale_info.dimension_type == "width"
        assert scale_info.uncertainty == "low"

    def test_build_scale_info_without_dimension(self, tmp_path: Path) -> None:
        """Test building scale info without known dimension."""
        project_dir = tmp_path / "test_project"
        initializer = ProjectInitializer(project_dir)

        scale_info = initializer._build_scale_info(None, None)

        assert scale_info.method == "realsense_depth_scale"
        assert scale_info.uncertainty == "medium"
