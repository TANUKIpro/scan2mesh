"""Tests for RGBDCapture stage."""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from scan2mesh.exceptions import CaptureError
from scan2mesh.models import (
    CameraIntrinsics,
    CapturePlan,
    CapturePlanPreset,
    RawFrame,
    ViewPoint,
)
from scan2mesh.services import MockCameraService
from scan2mesh.stages.capture import RGBDCapture


class TestRGBDCaptureInit:
    """Tests for RGBDCapture initialization."""

    def test_init_basic(self, tmp_path: Path) -> None:
        """Test basic initialization."""
        capture = RGBDCapture(tmp_path)
        assert capture.project_dir == tmp_path
        assert capture.is_capturing() is False

    def test_init_with_camera(self, tmp_path: Path) -> None:
        """Test initialization with camera."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)
        assert capture._camera is camera


class TestStartCapture:
    """Tests for start_capture method."""

    def test_start_capture_success(self, tmp_path: Path) -> None:
        """Test successful capture start."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        capture.start_capture()

        assert capture.is_capturing() is True
        assert camera.is_streaming is True

        capture.stop_capture()

    def test_start_capture_without_camera_raises(self, tmp_path: Path) -> None:
        """Test start capture without camera raises error."""
        capture = RGBDCapture(tmp_path)

        with pytest.raises(CaptureError, match="Camera not set"):
            capture.start_capture()

    def test_start_capture_already_capturing_raises(self, tmp_path: Path) -> None:
        """Test start capture when already capturing raises error."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        capture.start_capture()
        try:
            with pytest.raises(CaptureError, match="already in progress"):
                capture.start_capture()
        finally:
            capture.stop_capture()

    def test_start_capture_with_plan(self, tmp_path: Path) -> None:
        """Test start capture with capture plan."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        viewpoints = [
            ViewPoint(index=i, azimuth_deg=float(i * 30), elevation_deg=15.0, distance_m=0.4, order=i)
            for i in range(12)
        ]
        plan = CapturePlan(
            preset=CapturePlanPreset.QUICK,
            viewpoints=viewpoints,
            min_required_frames=12,
            recommended_distance_m=0.4,
        )

        capture.start_capture(plan=plan)
        assert capture._capture_plan is plan
        capture.stop_capture()


class TestCaptureFrame:
    """Tests for capture_frame method."""

    def test_capture_frame_success(self, tmp_path: Path) -> None:
        """Test successful frame capture."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        capture.start_capture()
        try:
            frame_data, quality = capture.capture_frame()

            assert frame_data.frame_id == 0
            assert frame_data.rgb_path.endswith(".png")
            assert frame_data.depth_path.endswith(".npy")
            assert 0.0 <= quality.blur_score <= 1.0
            assert 0.0 <= quality.depth_valid_ratio <= 1.0
        finally:
            capture.stop_capture()

    def test_capture_frame_not_capturing_raises(self, tmp_path: Path) -> None:
        """Test capture frame when not capturing raises error."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        with pytest.raises(CaptureError, match="not started"):
            capture.capture_frame()

    def test_capture_multiple_frames(self, tmp_path: Path) -> None:
        """Test capturing multiple frames."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        capture.start_capture()
        try:
            for i in range(5):
                frame_data, _ = capture.capture_frame()
                assert frame_data.frame_id == i

            assert capture.get_frame_count() == 5
        finally:
            capture.stop_capture()

    def test_capture_frame_saves_to_storage(self, tmp_path: Path) -> None:
        """Test that captured frames are saved to storage."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        capture.start_capture()
        try:
            frame_data, _ = capture.capture_frame()

            # Check files exist
            rgb_path = tmp_path / frame_data.rgb_path
            depth_path = tmp_path / frame_data.depth_path

            assert rgb_path.exists()
            assert depth_path.exists()
        finally:
            capture.stop_capture()


class TestEvaluateQuality:
    """Tests for evaluate_quality method."""

    def test_evaluate_quality_returns_frame_quality(self, tmp_path: Path) -> None:
        """Test evaluate_quality returns FrameQuality."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        intrinsics = CameraIntrinsics(
            width=640, height=480, fx=600.0, fy=600.0, cx=320.0, cy=240.0, depth_scale=0.001
        )
        raw_frame = RawFrame(
            rgb=np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8),
            depth=np.random.randint(300, 800, (480, 640), dtype=np.uint16),
            timestamp=datetime.now(),
            intrinsics=intrinsics,
        )

        quality = capture.evaluate_quality(raw_frame)

        assert 0.0 <= quality.blur_score <= 1.0
        assert 0.0 <= quality.depth_valid_ratio <= 1.0
        assert 0.0 <= quality.object_occupancy <= 1.0
        assert isinstance(quality.is_keyframe, bool)

    def test_evaluate_quality_high_quality_frame(self, tmp_path: Path) -> None:
        """Test that high quality frames are marked as keyframes."""
        capture = RGBDCapture(tmp_path)

        intrinsics = CameraIntrinsics(
            width=100, height=100, fx=50.0, fy=50.0, cx=50.0, cy=50.0, depth_scale=0.001
        )

        # Create sharp image with checkerboard pattern
        rgb = np.zeros((100, 100, 3), dtype=np.uint8)
        for i in range(100):
            for j in range(100):
                if (i // 10 + j // 10) % 2 == 0:
                    rgb[i, j] = [255, 255, 255]

        # Create depth image with object in center (within 200-1000mm range)
        depth = np.full((100, 100), 500, dtype=np.uint16)

        raw_frame = RawFrame(
            rgb=rgb,
            depth=depth,
            timestamp=datetime.now(),
            intrinsics=intrinsics,
        )

        quality = capture.evaluate_quality(raw_frame)

        # High quality frame should have good scores
        assert quality.depth_valid_ratio == 1.0  # All pixels valid
        assert quality.object_occupancy == 1.0  # All in range


class TestStopCapture:
    """Tests for stop_capture method."""

    def test_stop_capture_returns_metrics(self, tmp_path: Path) -> None:
        """Test stop_capture returns CaptureMetrics."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        capture.start_capture()
        for _ in range(5):
            capture.capture_frame()

        metrics = capture.stop_capture()

        assert metrics.num_frames_raw == 5
        assert 0.0 <= metrics.depth_valid_ratio_mean <= 1.0
        assert 0.0 <= metrics.blur_score_mean <= 1.0
        assert metrics.capture_duration_sec >= 0

    def test_stop_capture_not_capturing_raises(self, tmp_path: Path) -> None:
        """Test stop capture when not capturing raises error."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        with pytest.raises(CaptureError, match="not started"):
            capture.stop_capture()

    def test_stop_capture_saves_metadata(self, tmp_path: Path) -> None:
        """Test stop_capture saves frames metadata."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        capture.start_capture()
        for _ in range(3):
            capture.capture_frame()
        capture.stop_capture()

        # Check metadata file exists
        assert (tmp_path / "frames_metadata.json").exists()
        assert (tmp_path / "capture_metrics.json").exists()

    def test_stop_capture_stops_camera(self, tmp_path: Path) -> None:
        """Test stop_capture stops camera streaming."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        capture.start_capture()
        assert camera.is_streaming is True

        capture.stop_capture()
        assert camera.is_streaming is False


class TestSelectKeyframes:
    """Tests for _select_keyframes method."""

    def test_select_keyframes_empty(self, tmp_path: Path) -> None:
        """Test select keyframes with no frames."""
        capture = RGBDCapture(tmp_path)
        keyframes = capture._select_keyframes()
        assert keyframes == []

    def test_select_keyframes_identifies_keyframes(self, tmp_path: Path) -> None:
        """Test that keyframes are correctly identified."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        capture.start_capture()
        for _ in range(10):
            capture.capture_frame()

        keyframes = capture._select_keyframes()
        # Should have some keyframes based on quality
        assert isinstance(keyframes, list)
        assert all(isinstance(kf, int) for kf in keyframes)

        capture.stop_capture()


class TestEstimateCoverage:
    """Tests for estimate_coverage method."""

    def test_estimate_coverage_no_frames(self, tmp_path: Path) -> None:
        """Test coverage estimation with no frames."""
        capture = RGBDCapture(tmp_path)
        coverage = capture.estimate_coverage()
        assert coverage == 0.0

    def test_estimate_coverage_with_plan(self, tmp_path: Path) -> None:
        """Test coverage estimation with capture plan."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        viewpoints = [
            ViewPoint(index=i, azimuth_deg=float(i * 30), elevation_deg=15.0, distance_m=0.4, order=i)
            for i in range(12)
        ]
        plan = CapturePlan(
            preset=CapturePlanPreset.QUICK,
            viewpoints=viewpoints,
            min_required_frames=12,
            recommended_distance_m=0.4,
        )

        capture.start_capture(plan=plan)
        for _ in range(12):
            capture.capture_frame()

        coverage = capture.estimate_coverage()
        assert 0.0 <= coverage <= 1.0

        capture.stop_capture()


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_frame_count(self, tmp_path: Path) -> None:
        """Test get_frame_count returns correct count."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        assert capture.get_frame_count() == 0

        capture.start_capture()
        for i in range(3):
            capture.capture_frame()
            assert capture.get_frame_count() == i + 1
        capture.stop_capture()

    def test_get_keyframe_count(self, tmp_path: Path) -> None:
        """Test get_keyframe_count returns correct count."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        capture.start_capture()
        for _ in range(5):
            capture.capture_frame()

        keyframe_count = capture.get_keyframe_count()
        assert keyframe_count >= 0
        assert keyframe_count <= 5

        capture.stop_capture()

    def test_is_capturing(self, tmp_path: Path) -> None:
        """Test is_capturing returns correct state."""
        camera = MockCameraService(seed=42)
        capture = RGBDCapture(tmp_path, camera=camera)

        assert capture.is_capturing() is False

        capture.start_capture()
        assert capture.is_capturing() is True

        capture.stop_capture()
        assert capture.is_capturing() is False

    def test_set_camera(self, tmp_path: Path) -> None:
        """Test set_camera method."""
        capture = RGBDCapture(tmp_path)
        camera = MockCameraService(seed=42)

        capture.set_camera(camera)
        assert capture._camera is camera
