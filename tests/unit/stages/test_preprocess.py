"""Tests for Preprocessor stage."""

from pathlib import Path

import numpy as np
import pytest

from scan2mesh.models import MaskMethod
from scan2mesh.stages.preprocess import Preprocessor


class TestPreprocessorInit:
    """Tests for Preprocessor initialization."""

    def test_init_basic(self, tmp_path: Path) -> None:
        """Test basic initialization."""
        preprocessor = Preprocessor(tmp_path)
        assert preprocessor.project_dir == tmp_path
        assert preprocessor.depth_min_mm == Preprocessor.DEFAULT_DEPTH_MIN_MM
        assert preprocessor.depth_max_mm == Preprocessor.DEFAULT_DEPTH_MAX_MM

    def test_init_with_custom_thresholds(self, tmp_path: Path) -> None:
        """Test initialization with custom depth thresholds."""
        preprocessor = Preprocessor(
            tmp_path, depth_min_mm=100, depth_max_mm=500
        )
        assert preprocessor.depth_min_mm == 100
        assert preprocessor.depth_max_mm == 500


class TestFilterDepth:
    """Tests for filter_depth method."""

    def test_filter_depth_empty_raises(self, tmp_path: Path) -> None:
        """Test that empty depth image raises error."""
        preprocessor = Preprocessor(tmp_path)
        depth = np.array([], dtype=np.uint16)

        with pytest.raises(ValueError, match="empty"):
            preprocessor.filter_depth(depth)

    def test_filter_depth_invalid_shape_raises(self, tmp_path: Path) -> None:
        """Test that 3D depth image raises error."""
        preprocessor = Preprocessor(tmp_path)
        depth = np.zeros((10, 10, 3), dtype=np.uint16)

        with pytest.raises(ValueError, match="Expected 2D"):
            preprocessor.filter_depth(depth)

    def test_filter_depth_fills_small_holes(self, tmp_path: Path) -> None:
        """Test that small holes are filled."""
        preprocessor = Preprocessor(tmp_path)

        # Create depth with a small hole in the middle
        depth = np.full((10, 10), 500, dtype=np.uint16)
        depth[5, 5] = 0  # Small hole

        filtered = preprocessor.filter_depth(depth)

        # The hole should be filled
        assert filtered[5, 5] > 0

    def test_filter_depth_preserves_edges(self, tmp_path: Path) -> None:
        """Test that depth edges are preserved."""
        preprocessor = Preprocessor(tmp_path)

        # Create depth with large invalid region
        depth = np.zeros((10, 10), dtype=np.uint16)
        depth[2:8, 2:8] = 500  # Valid center region

        filtered = preprocessor.filter_depth(depth)

        # Center should still be valid
        assert np.all(filtered[3:7, 3:7] > 0)

    def test_filter_depth_removes_outliers(self, tmp_path: Path) -> None:
        """Test that outliers are smoothed."""
        preprocessor = Preprocessor(tmp_path)

        # Create depth with an outlier
        depth = np.full((10, 10), 500, dtype=np.uint16)
        depth[5, 5] = 5000  # Outlier

        filtered = preprocessor.filter_depth(depth)

        # The outlier should be smoothed
        assert filtered[5, 5] < 5000
        # Should be closer to neighbors
        assert abs(filtered[5, 5] - 500) < abs(5000 - 500)


class TestCreateMask:
    """Tests for create_mask method."""

    def test_create_mask_empty_raises(self, tmp_path: Path) -> None:
        """Test that empty depth image raises error."""
        preprocessor = Preprocessor(tmp_path)
        depth = np.array([], dtype=np.uint16)

        with pytest.raises(ValueError, match="empty"):
            preprocessor.create_mask(depth)

    def test_create_mask_depth_threshold(self, tmp_path: Path) -> None:
        """Test depth threshold masking."""
        preprocessor = Preprocessor(
            tmp_path, depth_min_mm=200, depth_max_mm=1000
        )

        # Create depth with known values
        depth = np.zeros((10, 10), dtype=np.uint16)
        depth[2:8, 2:8] = 500  # Within range
        depth[0:2, :] = 100  # Too close
        depth[8:10, :] = 1500  # Too far

        mask = preprocessor.create_mask(depth, MaskMethod.DEPTH_THRESHOLD)

        # Check mask values
        assert mask.dtype == np.uint8
        assert np.all(mask[2:8, 2:8] == 255)  # Foreground
        assert np.all(mask[0:2, :] == 0)  # Background (too close)
        assert np.all(mask[8:10, :] == 0)  # Background (too far)

    def test_create_mask_floor_plane(self, tmp_path: Path) -> None:
        """Test floor plane masking."""
        preprocessor = Preprocessor(
            tmp_path, depth_min_mm=200, depth_max_mm=1000
        )

        # Create depth simulating a flat floor
        depth = np.full((100, 100), 500, dtype=np.uint16)

        mask = preprocessor.create_mask(depth, MaskMethod.FLOOR_PLANE)

        # Should produce a valid mask
        assert mask.dtype == np.uint8
        assert mask.shape == (100, 100)

    def test_create_mask_unsupported_method_raises(self, tmp_path: Path) -> None:
        """Test that unsupported method raises error."""
        preprocessor = Preprocessor(tmp_path)
        depth = np.full((10, 10), 500, dtype=np.uint16)

        with pytest.raises(ValueError, match="Unsupported"):
            preprocessor.create_mask(depth, MaskMethod.MANUAL_BOUNDING)


class TestApplyMask:
    """Tests for apply_mask method."""

    def test_apply_mask_to_rgb(self, tmp_path: Path) -> None:
        """Test mask application to RGB image."""
        preprocessor = Preprocessor(tmp_path)

        rgb = np.full((10, 10, 3), 128, dtype=np.uint8)
        depth = np.full((10, 10), 500, dtype=np.uint16)

        # Mask with half foreground
        mask = np.zeros((10, 10), dtype=np.uint8)
        mask[5:, :] = 255

        masked_rgb, _masked_depth = preprocessor.apply_mask(rgb, depth, mask)

        # Check masked RGB
        assert np.all(masked_rgb[:5, :] == 0)  # Background is black
        assert np.all(masked_rgb[5:, :] == 128)  # Foreground preserved

    def test_apply_mask_to_depth(self, tmp_path: Path) -> None:
        """Test mask application to depth image."""
        preprocessor = Preprocessor(tmp_path)

        rgb = np.full((10, 10, 3), 128, dtype=np.uint8)
        depth = np.full((10, 10), 500, dtype=np.uint16)

        # Mask with half foreground
        mask = np.zeros((10, 10), dtype=np.uint8)
        mask[5:, :] = 255

        _, masked_depth = preprocessor.apply_mask(rgb, depth, mask)

        # Check masked depth
        assert np.all(masked_depth[:5, :] == 0)  # Background is 0
        assert np.all(masked_depth[5:, :] == 500)  # Foreground preserved


class TestDepthToPoints:
    """Tests for _depth_to_points helper method."""

    def test_depth_to_points_basic(self, tmp_path: Path) -> None:
        """Test basic depth to points conversion."""
        preprocessor = Preprocessor(tmp_path)

        depth = np.array([[500, 500], [500, 500]], dtype=np.uint16)
        mask = np.ones((2, 2), dtype=bool)

        points = preprocessor._depth_to_points(depth, mask)

        assert points.shape[0] == 4  # 4 points
        assert points.shape[1] == 3  # 3D coordinates


class TestFitPlaneRansac:
    """Tests for _fit_plane_ransac helper method."""

    def test_fit_plane_ransac_basic(self, tmp_path: Path) -> None:
        """Test basic plane fitting."""
        preprocessor = Preprocessor(tmp_path)

        # Create points on a plane z = 500
        x = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2], dtype=np.float64)
        y = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2], dtype=np.float64)
        z = np.full(9, 500, dtype=np.float64)
        points = np.stack([x, y, z], axis=1)

        # Add small noise
        points += np.random.randn(9, 3) * 0.1

        plane = preprocessor._fit_plane_ransac(points)

        assert plane is not None
        _a, _b, c, _d = plane
        # For z = 500 plane, normal should be (0, 0, 1) and d = -500
        assert abs(c) > 0.9  # Normal mostly in z direction

    def test_fit_plane_ransac_insufficient_points(self, tmp_path: Path) -> None:
        """Test plane fitting with insufficient points."""
        preprocessor = Preprocessor(tmp_path)

        points = np.array([[0, 0, 500], [1, 0, 500]], dtype=np.float64)

        plane = preprocessor._fit_plane_ransac(points)

        assert plane is None


class TestPreprocessorIntegration:
    """Integration tests for Preprocessor."""

    def test_preprocess_no_keyframes(self, tmp_path: Path) -> None:
        """Test preprocessing with no keyframes."""
        # Set up project structure
        (tmp_path / "raw_frames").mkdir()

        # Create minimal frames_metadata.json
        import json
        frames_metadata = {
            "frames": [],
            "keyframe_ids": [],
            "camera_intrinsics": {
                "width": 640,
                "height": 480,
                "fx": 600.0,
                "fy": 600.0,
                "cx": 320.0,
                "cy": 240.0,
                "depth_scale": 0.001,
            },
        }
        (tmp_path / "frames_metadata.json").write_text(json.dumps(frames_metadata))

        preprocessor = Preprocessor(tmp_path)
        metrics = preprocessor.preprocess()

        assert metrics.num_input_frames == 0
        assert metrics.num_output_frames == 0
        assert metrics.valid_frames_ratio == 0.0
