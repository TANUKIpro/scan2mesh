"""Frame preprocessing stage.

This module provides the Preprocessor class for preparing captured frames.
"""

import logging
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from scan2mesh.models import MaskedFrame, MaskMethod, PreprocessMetrics
from scan2mesh.services import ImageService, StorageService


logger = logging.getLogger("scan2mesh.stages.preprocess")


class Preprocessor:
    """Preprocess captured frames for reconstruction.

    This stage handles:
    - Depth filtering (hole filling, outlier removal)
    - Background removal using depth threshold or floor plane estimation
    - Frame filtering and enhancement

    Attributes:
        project_dir: Path to the project directory
        storage: Storage service instance
        image_service: Image analysis service
        depth_min_mm: Minimum depth threshold in mm
        depth_max_mm: Maximum depth threshold in mm
    """

    # Default depth thresholds
    DEFAULT_DEPTH_MIN_MM = 200
    DEFAULT_DEPTH_MAX_MM = 1000

    # Filter parameters
    MEDIAN_FILTER_SIZE = 5
    HOLE_FILL_ITERATIONS = 2

    # RANSAC parameters for floor plane estimation
    RANSAC_ITERATIONS = 100
    RANSAC_DISTANCE_THRESHOLD = 10  # mm

    def __init__(
        self,
        project_dir: Path,
        storage: StorageService | None = None,
        image_service: ImageService | None = None,
        depth_min_mm: int = DEFAULT_DEPTH_MIN_MM,
        depth_max_mm: int = DEFAULT_DEPTH_MAX_MM,
    ) -> None:
        """Initialize Preprocessor.

        Args:
            project_dir: Path to the project directory
            storage: Storage service instance (optional)
            image_service: Image analysis service instance (optional)
            depth_min_mm: Minimum depth threshold in mm
            depth_max_mm: Maximum depth threshold in mm
        """
        self.project_dir = project_dir
        self.storage = storage or StorageService(project_dir)
        self.image_service = image_service or ImageService()
        self.depth_min_mm = depth_min_mm
        self.depth_max_mm = depth_max_mm

    def filter_depth(self, depth: NDArray[np.uint16]) -> NDArray[np.uint16]:
        """Filter depth image to reduce noise and fill small holes.

        Args:
            depth: Depth image as numpy array (H, W), uint16 (mm)

        Returns:
            Filtered depth image

        Raises:
            ValueError: If depth image is empty or has invalid shape
        """
        if depth.size == 0:
            raise ValueError("Depth image is empty")

        if len(depth.shape) != 2:
            raise ValueError(f"Expected 2D depth image, got shape {depth.shape}")

        # Convert to float for processing
        depth_float = depth.astype(np.float64)

        # Step 1: Apply median filter for outlier removal
        filtered = self._apply_median_filter(depth_float)

        # Step 2: Fill small holes using morphological operations
        filled = self._fill_holes(filtered)

        # Convert back to uint16
        result = np.clip(filled, 0, 65535).astype(np.uint16)

        return result

    def _apply_median_filter(
        self, depth: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """Apply median filter to depth image.

        Simple median filter implementation without scipy.

        Args:
            depth: Depth image as float array

        Returns:
            Filtered depth image
        """
        h, w = depth.shape
        pad = self.MEDIAN_FILTER_SIZE // 2
        result = depth.copy()

        # Pad the image
        padded = np.pad(depth, pad, mode="reflect")

        # Apply median filter only to valid (non-zero) regions
        for y in range(h):
            for x in range(w):
                if depth[y, x] > 0:  # Only process valid pixels
                    window = padded[y : y + self.MEDIAN_FILTER_SIZE, x : x + self.MEDIAN_FILTER_SIZE]
                    valid_values = window[window > 0]
                    if len(valid_values) > 0:
                        result[y, x] = np.median(valid_values)

        return result

    def _fill_holes(self, depth: NDArray[np.float64]) -> NDArray[np.float64]:
        """Fill small holes in depth image using dilation.

        Args:
            depth: Depth image as float array

        Returns:
            Depth image with small holes filled
        """
        result = depth.copy()

        for _ in range(self.HOLE_FILL_ITERATIONS):
            # Find holes (zero values with valid neighbors)
            holes = result == 0
            if not np.any(holes):
                break

            # Simple dilation: replace holes with average of valid neighbors
            h, w = result.shape
            filled = result.copy()

            for y in range(1, h - 1):
                for x in range(1, w - 1):
                    if holes[y, x]:
                        # Get 3x3 neighborhood
                        neighborhood = result[y - 1 : y + 2, x - 1 : x + 2]
                        valid_neighbors = neighborhood[neighborhood > 0]
                        if len(valid_neighbors) >= 4:  # At least 4 valid neighbors
                            filled[y, x] = np.mean(valid_neighbors)

            result = filled

        return result

    def create_mask(
        self,
        depth: NDArray[np.uint16],
        method: MaskMethod = MaskMethod.DEPTH_THRESHOLD,
    ) -> NDArray[np.uint8]:
        """Create background removal mask.

        Args:
            depth: Depth image as numpy array (H, W), uint16 (mm)
            method: Masking method to use

        Returns:
            Binary mask image (H, W), uint8, 255=foreground, 0=background

        Raises:
            ValueError: If depth image is empty or method is unsupported
        """
        if depth.size == 0:
            raise ValueError("Depth image is empty")

        if method == MaskMethod.DEPTH_THRESHOLD:
            return self._create_depth_threshold_mask(depth)
        elif method == MaskMethod.FLOOR_PLANE:
            return self._create_floor_plane_mask(depth)
        else:
            raise ValueError(f"Unsupported mask method: {method}")

    def _create_depth_threshold_mask(
        self, depth: NDArray[np.uint16]
    ) -> NDArray[np.uint8]:
        """Create mask using depth thresholding.

        Pixels within [depth_min_mm, depth_max_mm] are considered foreground.

        Args:
            depth: Depth image

        Returns:
            Binary mask image
        """
        # Valid depth within range
        mask = (depth > self.depth_min_mm) & (depth < self.depth_max_mm)

        # Convert to uint8 (0 or 255)
        return (mask.astype(np.uint8) * 255)

    def _create_floor_plane_mask(
        self, depth: NDArray[np.uint16]
    ) -> NDArray[np.uint8]:
        """Create mask by estimating and removing floor plane.

        Uses RANSAC to fit a plane to the bottom portion of the depth image,
        then removes pixels on or below the plane.

        Args:
            depth: Depth image

        Returns:
            Binary mask image
        """
        h, _w = depth.shape

        # First, apply depth threshold to get candidate points
        valid_mask = (depth > self.depth_min_mm) & (depth < self.depth_max_mm)

        # Use bottom 30% of image as floor candidates
        floor_region = int(h * 0.7)
        floor_candidates = np.zeros_like(valid_mask)
        floor_candidates[floor_region:, :] = valid_mask[floor_region:, :]

        # Get 3D points from floor candidates
        points = self._depth_to_points(depth, floor_candidates)

        if len(points) < 3:
            # Not enough points for plane fitting, fall back to depth threshold
            logger.warning("Not enough points for floor plane estimation, falling back to depth threshold")
            return self._create_depth_threshold_mask(depth)

        # Fit plane using RANSAC
        plane_params = self._fit_plane_ransac(points)

        if plane_params is None:
            logger.warning("Floor plane fitting failed, falling back to depth threshold")
            return self._create_depth_threshold_mask(depth)

        # Create mask: keep points above the plane
        mask = self._filter_by_plane(depth, valid_mask, plane_params)

        return mask

    def _depth_to_points(
        self,
        depth: NDArray[np.uint16],
        mask: NDArray[np.bool_],
    ) -> NDArray[np.float64]:
        """Convert depth image to 3D points.

        Uses simple pinhole camera model with default intrinsics.

        Args:
            depth: Depth image
            mask: Mask of valid pixels

        Returns:
            Array of 3D points (N, 3)
        """
        h, w = depth.shape

        # Create coordinate grids
        y_coords, x_coords = np.where(mask)
        z_values = depth[mask].astype(np.float64)

        # Simple projection (assuming centered principal point)
        cx, cy = w / 2, h / 2
        fx = fy = max(w, h)  # Approximate focal length

        x_3d = (x_coords - cx) * z_values / fx
        y_3d = (y_coords - cy) * z_values / fy
        z_3d = z_values

        points = np.stack([x_3d, y_3d, z_3d], axis=1)

        return points

    def _fit_plane_ransac(
        self, points: NDArray[np.float64]
    ) -> tuple[float, float, float, float] | None:
        """Fit a plane to 3D points using RANSAC.

        Args:
            points: Array of 3D points (N, 3)

        Returns:
            Plane parameters (a, b, c, d) for ax + by + cz + d = 0, or None if failed
        """
        n_points = len(points)
        if n_points < 3:
            return None

        best_inliers = 0
        best_params: tuple[float, float, float, float] | None = None

        for _ in range(self.RANSAC_ITERATIONS):
            # Randomly select 3 points
            indices = np.random.choice(n_points, 3, replace=False)
            p1, p2, p3 = points[indices]

            # Compute plane normal
            v1 = p2 - p1
            v2 = p3 - p1
            normal = np.cross(v1, v2)

            # Normalize
            norm_length = np.linalg.norm(normal)
            if norm_length < 1e-10:
                continue

            normal = normal / norm_length
            a, b, c = normal
            d = -np.dot(normal, p1)

            # Count inliers
            distances = np.abs(np.dot(points, normal) + d)
            inliers = np.sum(distances < self.RANSAC_DISTANCE_THRESHOLD)

            if inliers > best_inliers:
                best_inliers = inliers
                best_params = (float(a), float(b), float(c), float(d))

        return best_params

    def _filter_by_plane(
        self,
        depth: NDArray[np.uint16],
        valid_mask: NDArray[np.bool_],
        plane_params: tuple[float, float, float, float],
    ) -> NDArray[np.uint8]:
        """Filter points by plane: keep points above the plane.

        Args:
            depth: Depth image
            valid_mask: Mask of valid depth pixels
            plane_params: Plane parameters (a, b, c, d)

        Returns:
            Binary mask image
        """
        h, w = depth.shape
        a, b, c, d = plane_params

        # Create mask for points above the plane
        result = np.zeros((h, w), dtype=np.uint8)

        # Get all valid points
        y_coords, x_coords = np.where(valid_mask)
        z_values = depth[valid_mask].astype(np.float64)

        # Convert to 3D
        cx, cy = w / 2, h / 2
        fx = fy = max(w, h)

        x_3d = (x_coords - cx) * z_values / fx
        y_3d = (y_coords - cy) * z_values / fy

        # Calculate signed distance to plane
        # Positive = above plane (if normal points up)
        distances = a * x_3d + b * y_3d + c * z_values + d

        # We want points above the floor, so filter based on sign
        # Assuming floor normal points up (negative y in image coords)
        above_plane = distances > self.RANSAC_DISTANCE_THRESHOLD

        # Set mask values
        result[y_coords[above_plane], x_coords[above_plane]] = 255

        return result

    def apply_mask(
        self,
        rgb: NDArray[np.uint8],
        depth: NDArray[np.uint16],
        mask: NDArray[np.uint8],
    ) -> tuple[NDArray[np.uint8], NDArray[np.uint16]]:
        """Apply mask to RGB and depth images.

        Args:
            rgb: RGB image as numpy array (H, W, 3)
            depth: Depth image as numpy array (H, W)
            mask: Binary mask (H, W), 255=foreground, 0=background

        Returns:
            Tuple of (masked_rgb, masked_depth)
        """
        # Create boolean mask
        bool_mask = mask > 0

        # Apply to RGB (set background to black)
        masked_rgb = rgb.copy()
        masked_rgb[~bool_mask] = 0

        # Apply to depth (set background to 0)
        masked_depth = depth.copy()
        masked_depth[~bool_mask] = 0

        return masked_rgb, masked_depth

    def preprocess(
        self,
        mask_method: MaskMethod = MaskMethod.DEPTH_THRESHOLD,
    ) -> PreprocessMetrics:
        """Run full preprocessing pipeline.

        Args:
            mask_method: Method to use for background removal

        Returns:
            PreprocessMetrics summarizing the preprocessing session
        """
        logger.info(f"Starting preprocessing with method: {mask_method.value}")

        # Load frames metadata
        frames_metadata = self.storage.load_frames_metadata()
        keyframe_ids = frames_metadata.keyframe_ids

        if not keyframe_ids:
            logger.warning("No keyframes found")
            return PreprocessMetrics(
                num_input_frames=0,
                num_output_frames=0,
                mask_method=mask_method,
                mask_area_ratio_mean=0.0,
                mask_area_ratio_min=0.0,
                valid_frames_ratio=0.0,
                gate_status="pending",
                gate_reasons=["No keyframes to process"],
            )

        num_input = len(keyframe_ids)
        processed_frames: list[MaskedFrame] = []
        mask_area_ratios: list[float] = []

        for frame_id in keyframe_ids:
            try:
                # Load frame data
                rgb, depth = self.storage.load_frame_data(frame_id)

                # Filter depth
                filtered_depth = self.filter_depth(depth)

                # Create mask
                mask = self.create_mask(filtered_depth, mask_method)

                # Calculate mask area ratio
                mask_area_ratio = float(np.sum(mask > 0) / mask.size)

                # Check if mask is valid (not too small or too large)
                is_valid = 0.05 < mask_area_ratio < 0.95

                if not is_valid:
                    logger.warning(
                        f"Frame {frame_id}: invalid mask area ratio {mask_area_ratio:.2%}"
                    )

                # Apply mask
                masked_rgb, masked_depth = self.apply_mask(rgb, filtered_depth, mask)

                # Save masked frame
                rgb_path, depth_path, mask_path = self.storage.save_masked_frame_data(
                    frame_id, masked_rgb, masked_depth, mask
                )

                # Record masked frame data
                masked_frame = MaskedFrame(
                    frame_id=frame_id,
                    rgb_masked_path=rgb_path,
                    depth_masked_path=depth_path,
                    mask_path=mask_path,
                    mask_method=mask_method,
                    mask_area_ratio=mask_area_ratio,
                    is_valid=is_valid,
                )
                processed_frames.append(masked_frame)
                mask_area_ratios.append(mask_area_ratio)

                logger.debug(
                    f"Frame {frame_id}: mask_area_ratio={mask_area_ratio:.2%}, valid={is_valid}"
                )

            except Exception as e:
                logger.error(f"Failed to process frame {frame_id}: {e}")
                continue

        # Calculate metrics
        num_output = len(processed_frames)
        num_valid = len([f for f in processed_frames if f.is_valid])

        if mask_area_ratios:
            mask_area_ratio_mean = float(np.mean(mask_area_ratios))
            mask_area_ratio_min = float(np.min(mask_area_ratios))
        else:
            mask_area_ratio_mean = 0.0
            mask_area_ratio_min = 0.0

        valid_frames_ratio = num_valid / num_input if num_input > 0 else 0.0

        metrics = PreprocessMetrics(
            num_input_frames=num_input,
            num_output_frames=num_output,
            mask_method=mask_method,
            mask_area_ratio_mean=mask_area_ratio_mean,
            mask_area_ratio_min=mask_area_ratio_min,
            valid_frames_ratio=valid_frames_ratio,
            gate_status="pending",
            gate_reasons=[],
        )

        # Save metrics
        self.storage.save_preprocess_metrics(metrics)

        logger.info(
            f"Preprocessing complete: {num_output}/{num_input} frames processed, "
            f"{num_valid} valid"
        )

        return metrics
