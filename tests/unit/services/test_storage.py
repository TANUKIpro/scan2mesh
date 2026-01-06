"""Tests for scan2mesh.services.storage module."""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from scan2mesh.exceptions import ConfigError
from scan2mesh.models import (
    CameraIntrinsics,
    CaptureMetrics,
    CapturePlan,
    CapturePlanPreset,
    FrameData,
    FrameQuality,
    FramesMetadata,
    ProjectConfig,
    ViewPoint,
)
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


class TestSaveCapturePlan:
    """Tests for save_capture_plan method."""

    def test_save_capture_plan(self, tmp_path: Path) -> None:
        """Test saving capture plan."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        viewpoints = [
            ViewPoint(
                index=0,
                azimuth_deg=0.0,
                elevation_deg=0.0,
                distance_m=0.4,
                order=0,
            ),
            ViewPoint(
                index=1,
                azimuth_deg=45.0,
                elevation_deg=0.0,
                distance_m=0.4,
                order=1,
            ),
        ]

        plan = CapturePlan(
            preset=CapturePlanPreset.QUICK,
            viewpoints=viewpoints,
            min_required_frames=12,
            recommended_distance_m=0.4,
            notes=["Test note"],
        )

        service.save_capture_plan(plan)

        assert service.capture_plan_path.exists()
        content = service.capture_plan_path.read_text()
        assert "quick" in content
        assert "0.4" in content

    def test_save_capture_plan_path(self, tmp_path: Path) -> None:
        """Test capture_plan_path property."""
        service = StorageService(tmp_path)
        assert service.capture_plan_path == tmp_path / "capture_plan.json"


class TestLoadCapturePlan:
    """Tests for load_capture_plan method."""

    def test_load_capture_plan(self, tmp_path: Path) -> None:
        """Test loading capture plan."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        # Create capture plan file
        plan_data = {
            "preset": "standard",
            "viewpoints": [
                {
                    "index": 0,
                    "azimuth_deg": 0.0,
                    "elevation_deg": 15.0,
                    "distance_m": 0.4,
                    "order": 0,
                }
            ],
            "min_required_frames": 20,
            "recommended_distance_m": 0.4,
            "notes": [],
        }

        import json

        service.capture_plan_path.write_text(json.dumps(plan_data))

        plan = service.load_capture_plan()

        assert plan.preset == CapturePlanPreset.STANDARD
        assert len(plan.viewpoints) == 1
        assert plan.min_required_frames == 20

    def test_load_capture_plan_missing_file(self, tmp_path: Path) -> None:
        """Test loading nonexistent capture plan raises error."""
        service = StorageService(tmp_path)

        with pytest.raises(ConfigError, match="not found"):
            service.load_capture_plan()

    def test_load_capture_plan_invalid_data(self, tmp_path: Path) -> None:
        """Test loading invalid capture plan raises error."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        # Create invalid plan file
        service.capture_plan_path.write_text('{"invalid": "data"}')

        with pytest.raises(ConfigError, match="Invalid"):
            service.load_capture_plan()

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Test save and load roundtrip preserves data."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        viewpoints = [
            ViewPoint(
                index=i,
                azimuth_deg=float(i * 30),
                elevation_deg=15.0,
                distance_m=0.4,
                order=i,
            )
            for i in range(12)
        ]

        original = CapturePlan(
            preset=CapturePlanPreset.STANDARD,
            viewpoints=viewpoints,
            min_required_frames=20,
            recommended_distance_m=0.4,
            notes=["Note 1", "Note 2"],
        )

        service.save_capture_plan(original)
        loaded = service.load_capture_plan()

        assert loaded.preset == original.preset
        assert len(loaded.viewpoints) == len(original.viewpoints)
        assert loaded.min_required_frames == original.min_required_frames
        assert loaded.recommended_distance_m == original.recommended_distance_m
        assert loaded.notes == original.notes


class TestSaveFrameData:
    """Tests for save_frame_data method."""

    def test_save_frame_data(self, tmp_path: Path) -> None:
        """Test saving frame data creates files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        rgb = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        depth = np.random.randint(0, 5000, (480, 640), dtype=np.uint16)

        rgb_path, depth_path = service.save_frame_data(0, rgb, depth)

        # Check paths are relative
        assert rgb_path == "raw_frames/frame_0000_rgb.png"
        assert depth_path == "raw_frames/frame_0000_depth.npy"

        # Check files exist
        assert (project_dir / rgb_path).exists()
        assert (project_dir / depth_path).exists()

    def test_save_frame_data_depth_roundtrip(self, tmp_path: Path) -> None:
        """Test depth data is saved losslessly."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        depth = np.random.randint(0, 5000, (240, 320), dtype=np.uint16)

        _, depth_path = service.save_frame_data(1, np.zeros((240, 320, 3), dtype=np.uint8), depth)

        # Load and compare
        loaded_depth = np.load(project_dir / depth_path)
        np.testing.assert_array_equal(loaded_depth, depth)

    def test_save_frame_data_creates_directory(self, tmp_path: Path) -> None:
        """Test save_frame_data creates raw_frames directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        rgb = np.zeros((100, 100, 3), dtype=np.uint8)
        depth = np.zeros((100, 100), dtype=np.uint16)

        service.save_frame_data(0, rgb, depth)

        assert (project_dir / "raw_frames").exists()
        assert (project_dir / "raw_frames").is_dir()

    def test_save_multiple_frames(self, tmp_path: Path) -> None:
        """Test saving multiple frames with sequential IDs."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        for i in range(3):
            rgb = np.zeros((100, 100, 3), dtype=np.uint8)
            depth = np.zeros((100, 100), dtype=np.uint16)
            rgb_path, depth_path = service.save_frame_data(i, rgb, depth)

            assert f"frame_{i:04d}" in rgb_path
            assert f"frame_{i:04d}" in depth_path


class TestGetFramePath:
    """Tests for get_frame_path method."""

    def test_get_frame_path_rgb(self, tmp_path: Path) -> None:
        """Test get_frame_path returns correct RGB path."""
        service = StorageService(tmp_path)
        path = service.get_frame_path(5, "rgb")
        assert path == tmp_path / "raw_frames" / "frame_0005_rgb.png"

    def test_get_frame_path_depth(self, tmp_path: Path) -> None:
        """Test get_frame_path returns correct depth path."""
        service = StorageService(tmp_path)
        path = service.get_frame_path(10, "depth")
        assert path == tmp_path / "raw_frames" / "frame_0010_depth.npy"

    def test_get_frame_path_default_rgb(self, tmp_path: Path) -> None:
        """Test get_frame_path defaults to RGB."""
        service = StorageService(tmp_path)
        path = service.get_frame_path(0)
        assert "rgb" in str(path)


class TestFramesMetadata:
    """Tests for frames metadata methods."""

    def test_save_frames_metadata(self, tmp_path: Path) -> None:
        """Test saving frames metadata."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        intrinsics = CameraIntrinsics(
            width=640, height=480, fx=600.0, fy=600.0, cx=320.0, cy=240.0, depth_scale=0.001
        )
        quality = FrameQuality(
            depth_valid_ratio=0.95, blur_score=0.8, object_occupancy=0.5
        )
        frame = FrameData(
            frame_id=0,
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            rgb_path="raw_frames/frame_0000_rgb.png",
            depth_path="raw_frames/frame_0000_depth.npy",
            intrinsics=intrinsics,
            quality=quality,
        )

        metadata = FramesMetadata(frames=[frame], total_frames=1, keyframe_ids=[0])

        service.save_frames_metadata(metadata)

        assert service.frames_metadata_path.exists()

    def test_load_frames_metadata(self, tmp_path: Path) -> None:
        """Test loading frames metadata."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        # Create metadata file
        import json

        metadata_data = {
            "frames": [
                {
                    "frame_id": 0,
                    "timestamp": "2025-01-01T12:00:00",
                    "rgb_path": "raw_frames/frame_0000_rgb.png",
                    "depth_path": "raw_frames/frame_0000_depth.npy",
                    "intrinsics": {
                        "width": 640,
                        "height": 480,
                        "fx": 600.0,
                        "fy": 600.0,
                        "cx": 320.0,
                        "cy": 240.0,
                        "depth_scale": 0.001,
                    },
                    "quality": {
                        "depth_valid_ratio": 0.95,
                        "blur_score": 0.8,
                        "object_occupancy": 0.5,
                        "is_keyframe": True,
                    },
                }
            ],
            "total_frames": 1,
            "keyframe_ids": [0],
        }
        service.frames_metadata_path.write_text(json.dumps(metadata_data))

        metadata = service.load_frames_metadata()

        assert metadata.total_frames == 1
        assert len(metadata.frames) == 1
        assert metadata.keyframe_ids == [0]

    def test_load_missing_frames_metadata_raises(self, tmp_path: Path) -> None:
        """Test loading nonexistent metadata raises error."""
        service = StorageService(tmp_path)

        with pytest.raises(ConfigError, match="not found"):
            service.load_frames_metadata()

    def test_frames_metadata_roundtrip(self, tmp_path: Path) -> None:
        """Test save and load roundtrip for frames metadata."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        intrinsics = CameraIntrinsics(
            width=1280, height=720, fx=640.0, fy=640.0, cx=640.0, cy=360.0, depth_scale=0.001
        )
        quality = FrameQuality(
            depth_valid_ratio=0.9, blur_score=0.7, object_occupancy=0.6, is_keyframe=True
        )
        frame = FrameData(
            frame_id=0,
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            rgb_path="raw_frames/frame_0000_rgb.png",
            depth_path="raw_frames/frame_0000_depth.npy",
            intrinsics=intrinsics,
            quality=quality,
        )

        original = FramesMetadata(frames=[frame], total_frames=5, keyframe_ids=[0, 2, 4])

        service.save_frames_metadata(original)
        loaded = service.load_frames_metadata()

        assert loaded.total_frames == original.total_frames
        assert len(loaded.frames) == len(original.frames)
        assert loaded.keyframe_ids == original.keyframe_ids


class TestCaptureMetrics:
    """Tests for capture metrics methods."""

    def test_save_capture_metrics(self, tmp_path: Path) -> None:
        """Test saving capture metrics."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        metrics = CaptureMetrics(
            num_frames_raw=100,
            num_keyframes=20,
            depth_valid_ratio_mean=0.92,
            depth_valid_ratio_min=0.85,
            blur_score_mean=0.75,
            blur_score_min=0.6,
            coverage_score=0.88,
            capture_duration_sec=120.5,
            gate_status="pass",
            gate_reasons=[],
        )

        service.save_capture_metrics(metrics)

        assert service.capture_metrics_path.exists()

    def test_load_capture_metrics(self, tmp_path: Path) -> None:
        """Test loading capture metrics."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        # Create metrics file
        import json

        metrics_data = {
            "num_frames_raw": 50,
            "num_keyframes": 15,
            "depth_valid_ratio_mean": 0.9,
            "depth_valid_ratio_min": 0.8,
            "blur_score_mean": 0.7,
            "blur_score_min": 0.5,
            "coverage_score": 0.85,
            "capture_duration_sec": 60.0,
            "gate_status": "warn",
            "gate_reasons": ["Low coverage"],
        }
        service.capture_metrics_path.write_text(json.dumps(metrics_data))

        metrics = service.load_capture_metrics()

        assert metrics.num_frames_raw == 50
        assert metrics.num_keyframes == 15
        assert metrics.gate_status == "warn"

    def test_load_missing_capture_metrics_raises(self, tmp_path: Path) -> None:
        """Test loading nonexistent metrics raises error."""
        service = StorageService(tmp_path)

        with pytest.raises(ConfigError, match="not found"):
            service.load_capture_metrics()

    def test_capture_metrics_roundtrip(self, tmp_path: Path) -> None:
        """Test save and load roundtrip for capture metrics."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        service = StorageService(project_dir)

        original = CaptureMetrics(
            num_frames_raw=75,
            num_keyframes=18,
            depth_valid_ratio_mean=0.88,
            depth_valid_ratio_min=0.75,
            blur_score_mean=0.82,
            blur_score_min=0.65,
            coverage_score=0.91,
            capture_duration_sec=95.3,
            gate_status="pass",
            gate_reasons=[],
        )

        service.save_capture_metrics(original)
        loaded = service.load_capture_metrics()

        assert loaded.num_frames_raw == original.num_frames_raw
        assert loaded.num_keyframes == original.num_keyframes
        assert loaded.gate_status == original.gate_status
