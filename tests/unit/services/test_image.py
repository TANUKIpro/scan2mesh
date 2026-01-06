"""Tests for ImageService."""

import numpy as np
import pytest

from scan2mesh.services.image import ImageService


class TestImageService:
    """Tests for ImageService class."""

    @pytest.fixture
    def service(self) -> ImageService:
        """Create ImageService instance."""
        return ImageService()

    # ============================================================
    # calculate_blur_score tests
    # ============================================================

    def test_calculate_blur_score_sharp_image(self, service: ImageService) -> None:
        """Sharp image with high frequency edges should have high score."""
        # Create image with sharp edges (checkerboard pattern)
        rgb = np.zeros((100, 100, 3), dtype=np.uint8)
        for i in range(100):
            for j in range(100):
                if (i // 10 + j // 10) % 2 == 0:
                    rgb[i, j] = [255, 255, 255]

        score = service.calculate_blur_score(rgb)

        assert 0.0 <= score <= 1.0
        # Sharp edges should give higher score
        assert score > 0.3

    def test_calculate_blur_score_blurry_image(self, service: ImageService) -> None:
        """Uniform image should have low blur score."""
        # Create uniform gray image (no edges)
        rgb = np.full((100, 100, 3), 128, dtype=np.uint8)

        score = service.calculate_blur_score(rgb)

        assert 0.0 <= score <= 1.0
        # No edges should give low score
        assert score < 0.1

    def test_calculate_blur_score_gradient_image(self, service: ImageService) -> None:
        """Image with gradual gradient should have moderate score."""
        # Create horizontal gradient
        rgb = np.zeros((100, 100, 3), dtype=np.uint8)
        for i in range(100):
            rgb[:, i] = [int(i * 2.55)] * 3

        score = service.calculate_blur_score(rgb)

        assert 0.0 <= score <= 1.0

    def test_calculate_blur_score_empty_image_raises(
        self, service: ImageService
    ) -> None:
        """Empty image should raise ValueError."""
        rgb = np.array([], dtype=np.uint8).reshape(0, 0, 3)

        with pytest.raises(ValueError, match="Image is empty"):
            service.calculate_blur_score(rgb)

    def test_calculate_blur_score_invalid_shape_raises(
        self, service: ImageService
    ) -> None:
        """Non-RGB image should raise ValueError."""
        gray = np.zeros((100, 100), dtype=np.uint8)

        with pytest.raises(ValueError, match="Expected RGB image"):
            service.calculate_blur_score(gray)  # type: ignore[arg-type]

    # ============================================================
    # calculate_depth_valid_ratio tests
    # ============================================================

    def test_calculate_depth_valid_ratio_all_valid(
        self, service: ImageService
    ) -> None:
        """All non-zero pixels should give ratio of 1.0."""
        depth = np.full((100, 100), 500, dtype=np.uint16)

        ratio = service.calculate_depth_valid_ratio(depth)

        assert ratio == 1.0

    def test_calculate_depth_valid_ratio_all_invalid(
        self, service: ImageService
    ) -> None:
        """All zero pixels should give ratio of 0.0."""
        depth = np.zeros((100, 100), dtype=np.uint16)

        ratio = service.calculate_depth_valid_ratio(depth)

        assert ratio == 0.0

    def test_calculate_depth_valid_ratio_half_valid(
        self, service: ImageService
    ) -> None:
        """Half valid pixels should give ratio of 0.5."""
        depth = np.zeros((100, 100), dtype=np.uint16)
        depth[:50, :] = 500

        ratio = service.calculate_depth_valid_ratio(depth)

        assert ratio == 0.5

    def test_calculate_depth_valid_ratio_empty_raises(
        self, service: ImageService
    ) -> None:
        """Empty depth image should raise ValueError."""
        depth = np.array([], dtype=np.uint16).reshape(0, 0)

        with pytest.raises(ValueError, match="Depth image is empty"):
            service.calculate_depth_valid_ratio(depth)

    # ============================================================
    # estimate_object_occupancy tests
    # ============================================================

    def test_estimate_object_occupancy_all_in_range(
        self, service: ImageService
    ) -> None:
        """All pixels in range should give occupancy of 1.0."""
        depth = np.full((100, 100), 500, dtype=np.uint16)  # 500mm, within default range

        occupancy = service.estimate_object_occupancy(depth)

        assert occupancy == 1.0

    def test_estimate_object_occupancy_none_in_range(
        self, service: ImageService
    ) -> None:
        """No pixels in range should give occupancy of 0.0."""
        depth = np.full((100, 100), 2000, dtype=np.uint16)  # 2000mm, outside default range

        occupancy = service.estimate_object_occupancy(depth)

        assert occupancy == 0.0

    def test_estimate_object_occupancy_custom_range(
        self, service: ImageService
    ) -> None:
        """Custom depth range should work correctly."""
        depth = np.full((100, 100), 500, dtype=np.uint16)

        # 500mm is within 300-600 range
        occupancy_in = service.estimate_object_occupancy(
            depth, min_depth_mm=300, max_depth_mm=600
        )
        assert occupancy_in == 1.0

        # 500mm is outside 600-800 range
        occupancy_out = service.estimate_object_occupancy(
            depth, min_depth_mm=600, max_depth_mm=800
        )
        assert occupancy_out == 0.0

    def test_estimate_object_occupancy_zero_depth(
        self, service: ImageService
    ) -> None:
        """Zero depth (invalid) should not count as in range."""
        depth = np.zeros((100, 100), dtype=np.uint16)

        occupancy = service.estimate_object_occupancy(depth)

        assert occupancy == 0.0

    def test_estimate_object_occupancy_empty_raises(
        self, service: ImageService
    ) -> None:
        """Empty depth image should raise ValueError."""
        depth = np.array([], dtype=np.uint16).reshape(0, 0)

        with pytest.raises(ValueError, match="Depth image is empty"):
            service.estimate_object_occupancy(depth)

    # ============================================================
    # calculate_depth_statistics tests
    # ============================================================

    def test_calculate_depth_statistics_normal(self, service: ImageService) -> None:
        """Normal depth image should return correct statistics."""
        # Create depth with known values
        depth = np.array([[400, 500], [600, 0]], dtype=np.uint16)

        stats = service.calculate_depth_statistics(depth)

        assert stats["valid_ratio"] == 0.75  # 3 out of 4 pixels
        assert stats["mean_depth_mm"] == 500.0  # (400 + 500 + 600) / 3
        assert stats["min_depth_mm"] == 400.0
        assert stats["max_depth_mm"] == 600.0
        assert stats["std_depth_mm"] > 0

    def test_calculate_depth_statistics_empty(self, service: ImageService) -> None:
        """Empty depth image should return zeros."""
        depth = np.array([], dtype=np.uint16).reshape(0, 0)

        stats = service.calculate_depth_statistics(depth)

        assert stats["valid_ratio"] == 0.0
        assert stats["mean_depth_mm"] == 0.0
        assert stats["std_depth_mm"] == 0.0

    def test_calculate_depth_statistics_all_zero(self, service: ImageService) -> None:
        """All zero depth should return zero statistics."""
        depth = np.zeros((10, 10), dtype=np.uint16)

        stats = service.calculate_depth_statistics(depth)

        assert stats["valid_ratio"] == 0.0
        assert stats["mean_depth_mm"] == 0.0
