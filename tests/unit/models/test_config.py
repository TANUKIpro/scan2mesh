"""Tests for scan2mesh.models.config module."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from scan2mesh.models.config import (
    CoordinateSystem,
    OutputPreset,
    ProjectConfig,
    ScaleInfo,
)


class TestCoordinateSystem:
    """Tests for CoordinateSystem model."""

    def test_default_values(self) -> None:
        """Test default coordinate system values."""
        coord = CoordinateSystem()
        assert coord.up_axis == "Z"
        assert coord.forward_axis == "Y"
        assert coord.origin == "bottom_center"

    def test_custom_values(self) -> None:
        """Test custom coordinate system values."""
        coord = CoordinateSystem(up_axis="Y", forward_axis="Z", origin="centroid")
        assert coord.up_axis == "Y"
        assert coord.forward_axis == "Z"
        assert coord.origin == "centroid"

    def test_invalid_up_axis(self) -> None:
        """Test invalid up axis validation."""
        with pytest.raises(ValidationError):
            CoordinateSystem(up_axis="W")

    def test_invalid_forward_axis(self) -> None:
        """Test invalid forward axis validation."""
        with pytest.raises(ValidationError):
            CoordinateSystem(forward_axis="invalid")


class TestOutputPreset:
    """Tests for OutputPreset model."""

    def test_default_values(self) -> None:
        """Test default output preset values."""
        preset = OutputPreset()
        assert preset.coordinate_system is not None
        assert preset.lod_triangle_limits == [100000, 30000, 10000]
        assert preset.texture_resolution == 2048
        assert preset.units == "meter"

    def test_custom_lod_levels(self) -> None:
        """Test custom LOD levels."""
        preset = OutputPreset(lod_triangle_limits=[50000, 25000])
        assert preset.lod_triangle_limits == [50000, 25000]


class TestScaleInfo:
    """Tests for ScaleInfo model."""

    def test_known_dimension_method(self) -> None:
        """Test known dimension scale method."""
        scale = ScaleInfo(
            method="known_dimension",
            known_dimension_mm=100.0,
            dimension_type="width",
            uncertainty="low",
        )
        assert scale.method == "known_dimension"
        assert scale.known_dimension_mm == 100.0
        assert scale.dimension_type == "width"

    def test_depth_scale_method(self) -> None:
        """Test RealSense depth scale method."""
        scale = ScaleInfo(method="realsense_depth_scale", uncertainty="medium")
        assert scale.method == "realsense_depth_scale"
        assert scale.known_dimension_mm is None

    def test_invalid_method(self) -> None:
        """Test invalid scale method validation."""
        with pytest.raises(ValidationError):
            ScaleInfo(method="invalid_method", uncertainty="low")

    def test_invalid_uncertainty(self) -> None:
        """Test invalid uncertainty validation."""
        with pytest.raises(ValidationError):
            ScaleInfo(method="realsense_depth_scale", uncertainty="maybe")


class TestProjectConfig:
    """Tests for ProjectConfig model."""

    def test_valid_config(self) -> None:
        """Test valid project configuration."""
        now = datetime.now()
        config = ProjectConfig(
            object_name="test_ball",
            class_id=42,
            config_hash="abc123",
            created_at=now,
            updated_at=now,
        )
        assert config.object_name == "test_ball"
        assert config.class_id == 42
        assert config.schema_version == "1.0"

    def test_object_name_validation(self) -> None:
        """Test object name validation."""
        now = datetime.now()
        # Valid names
        ProjectConfig(
            object_name="test_ball",
            class_id=0,
            config_hash="x",
            created_at=now,
            updated_at=now,
        )
        ProjectConfig(
            object_name="my-object",
            class_id=0,
            config_hash="x",
            created_at=now,
            updated_at=now,
        )
        ProjectConfig(
            object_name="Object123",
            class_id=0,
            config_hash="x",
            created_at=now,
            updated_at=now,
        )

        # Invalid names - empty
        with pytest.raises(ValidationError):
            ProjectConfig(
                object_name="",
                class_id=0,
                config_hash="x",
                created_at=now,
                updated_at=now,
            )

        # Invalid names - space (doesn't match pattern)
        with pytest.raises(ValidationError):
            ProjectConfig(
                object_name="test ball",
                class_id=0,
                config_hash="x",
                created_at=now,
                updated_at=now,
            )

        # Invalid names - slash (doesn't match pattern)
        with pytest.raises(ValidationError):
            ProjectConfig(
                object_name="test/ball",
                class_id=0,
                config_hash="x",
                created_at=now,
                updated_at=now,
            )

    def test_path_traversal_prevention(self) -> None:
        """Test path traversal attempt detection."""
        now = datetime.now()
        # These should fail the pattern validation, not just path traversal
        with pytest.raises(ValidationError):
            ProjectConfig(
                object_name="../etc",
                class_id=0,
                config_hash="x",
                created_at=now,
                updated_at=now,
            )

    def test_class_id_range(self) -> None:
        """Test class ID range validation."""
        now = datetime.now()
        # Valid IDs
        ProjectConfig(
            object_name="test",
            class_id=0,
            config_hash="x",
            created_at=now,
            updated_at=now,
        )
        ProjectConfig(
            object_name="test",
            class_id=9999,
            config_hash="x",
            created_at=now,
            updated_at=now,
        )

        # Invalid IDs
        with pytest.raises(ValidationError):
            ProjectConfig(
                object_name="test",
                class_id=-1,
                config_hash="x",
                created_at=now,
                updated_at=now,
            )

        with pytest.raises(ValidationError):
            ProjectConfig(
                object_name="test",
                class_id=10000,
                config_hash="x",
                created_at=now,
                updated_at=now,
            )

    def test_immutability(self) -> None:
        """Test that config is immutable (frozen)."""
        now = datetime.now()
        config = ProjectConfig(
            object_name="test",
            class_id=0,
            config_hash="x",
            created_at=now,
            updated_at=now,
        )
        with pytest.raises(ValidationError):
            config.object_name = "modified"  # type: ignore[misc]
