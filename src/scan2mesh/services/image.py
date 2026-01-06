"""Image processing service.

This module provides image processing utilities for capture quality assessment.
"""

import numpy as np
from numpy.typing import NDArray


class ImageService:
    """Service for image processing operations.

    Provides methods for calculating quality metrics on RGB and depth images.
    All methods are designed to work with numpy arrays only (no OpenCV dependency).
    """

    # Blur score normalization constants (empirical values)
    BLUR_LAPLACIAN_LOW = 100.0  # Below this: blurry
    BLUR_LAPLACIAN_HIGH = 500.0  # Above this: sharp

    def calculate_blur_score(self, rgb: NDArray[np.uint8]) -> float:
        """Calculate blur score using Laplacian variance.

        Uses a simplified Laplacian kernel to detect edges.
        Higher variance means sharper image.

        Args:
            rgb: RGB image as numpy array (H, W, 3), uint8

        Returns:
            Blur score between 0.0 (blurry) and 1.0 (sharp)

        Raises:
            ValueError: If image is empty or has invalid shape
        """
        if rgb.size == 0:
            raise ValueError("Image is empty")

        if len(rgb.shape) != 3 or rgb.shape[2] != 3:
            raise ValueError(f"Expected RGB image with shape (H, W, 3), got {rgb.shape}")

        # Convert to grayscale using luminosity method
        # Y = 0.299*R + 0.587*G + 0.114*B
        gray = (
            0.299 * rgb[:, :, 0].astype(np.float64)
            + 0.587 * rgb[:, :, 1].astype(np.float64)
            + 0.114 * rgb[:, :, 2].astype(np.float64)
        )

        # Apply Laplacian kernel
        # [0,  1, 0]
        # [1, -4, 1]
        # [0,  1, 0]
        laplacian = self._apply_laplacian(gray)

        # Calculate variance
        laplacian_var = np.var(laplacian)

        # Normalize to 0.0-1.0 range
        score = (laplacian_var - self.BLUR_LAPLACIAN_LOW) / (
            self.BLUR_LAPLACIAN_HIGH - self.BLUR_LAPLACIAN_LOW
        )

        return float(np.clip(score, 0.0, 1.0))

    def _apply_laplacian(self, gray: NDArray[np.float64]) -> NDArray[np.float64]:
        """Apply Laplacian kernel to grayscale image.

        Args:
            gray: Grayscale image as numpy array (H, W)

        Returns:
            Laplacian filtered image
        """
        # Pad image to handle borders
        padded = np.pad(gray, pad_width=1, mode="reflect")

        # Apply 3x3 Laplacian kernel using shifts
        # Center: -4 * center pixel
        # Neighbors: sum of 4 adjacent pixels
        laplacian = (
            -4 * gray
            + padded[:-2, 1:-1]  # top
            + padded[2:, 1:-1]  # bottom
            + padded[1:-1, :-2]  # left
            + padded[1:-1, 2:]  # right
        )

        return laplacian

    def calculate_depth_valid_ratio(self, depth: NDArray[np.uint16]) -> float:
        """Calculate the ratio of valid depth pixels.

        Valid pixels are those with non-zero depth values.

        Args:
            depth: Depth image as numpy array (H, W), uint16 (mm)

        Returns:
            Ratio of valid pixels between 0.0 and 1.0

        Raises:
            ValueError: If depth image is empty
        """
        if depth.size == 0:
            raise ValueError("Depth image is empty")

        total_pixels = depth.size
        valid_pixels = np.count_nonzero(depth)

        return float(valid_pixels / total_pixels)

    def estimate_object_occupancy(
        self,
        depth: NDArray[np.uint16],
        min_depth_mm: int = 200,
        max_depth_mm: int = 1000,
    ) -> float:
        """Estimate object occupancy in the frame.

        Calculates the ratio of pixels within the expected depth range
        that likely belong to the object.

        Args:
            depth: Depth image as numpy array (H, W), uint16 (mm)
            min_depth_mm: Minimum depth threshold in mm (default: 200mm)
            max_depth_mm: Maximum depth threshold in mm (default: 1000mm)

        Returns:
            Occupancy ratio between 0.0 and 1.0

        Raises:
            ValueError: If depth image is empty
        """
        if depth.size == 0:
            raise ValueError("Depth image is empty")

        # Create mask for valid depth range
        in_range_mask = (depth > min_depth_mm) & (depth < max_depth_mm)

        # Count pixels in range
        in_range_count = np.count_nonzero(in_range_mask)
        total_pixels = depth.size

        return float(in_range_count / total_pixels)

    def calculate_depth_statistics(
        self, depth: NDArray[np.uint16]
    ) -> dict[str, float]:
        """Calculate statistics for depth image.

        Args:
            depth: Depth image as numpy array (H, W), uint16 (mm)

        Returns:
            Dictionary with statistics:
            - valid_ratio: Ratio of valid (non-zero) pixels
            - mean_depth_mm: Mean depth of valid pixels
            - std_depth_mm: Standard deviation of valid pixels
            - min_depth_mm: Minimum valid depth
            - max_depth_mm: Maximum valid depth
        """
        if depth.size == 0:
            return {
                "valid_ratio": 0.0,
                "mean_depth_mm": 0.0,
                "std_depth_mm": 0.0,
                "min_depth_mm": 0.0,
                "max_depth_mm": 0.0,
            }

        valid_mask = depth > 0
        valid_depths = depth[valid_mask]

        if valid_depths.size == 0:
            return {
                "valid_ratio": 0.0,
                "mean_depth_mm": 0.0,
                "std_depth_mm": 0.0,
                "min_depth_mm": 0.0,
                "max_depth_mm": 0.0,
            }

        return {
            "valid_ratio": float(valid_depths.size / depth.size),
            "mean_depth_mm": float(np.mean(valid_depths)),
            "std_depth_mm": float(np.std(valid_depths)),
            "min_depth_mm": float(np.min(valid_depths)),
            "max_depth_mm": float(np.max(valid_depths)),
        }
