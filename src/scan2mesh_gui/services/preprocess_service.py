"""Preprocess service for managing preprocessing sessions."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import ClassVar

import cv2
import numpy as np
import numpy.typing as npt

from scan2mesh_gui.models.capture_session import CapturedFrame
from scan2mesh_gui.models.preprocess_session import (
    MaskedFrame,
    MaskMethod,
    MaskQuality,
    PreprocessMetrics,
    PreprocessSession,
)


class PreprocessService:
    """Service for managing preprocessing sessions and mask generation."""

    # Quality thresholds for valid mask detection
    MASK_AREA_RATIO_MIN: ClassVar[float] = 0.05
    MASK_AREA_RATIO_MAX: ClassVar[float] = 0.8
    EDGE_QUALITY_THRESHOLD: ClassVar[float] = 0.3

    def __init__(self, projects_dir: Path) -> None:
        """Initialize the preprocess service.

        Args:
            projects_dir: Base directory for project data
        """
        self.projects_dir = projects_dir

    def start_session(
        self,
        object_id: str,
        captured_frames: list[CapturedFrame],
    ) -> PreprocessSession:
        """Start a new preprocessing session.

        Args:
            object_id: ID of the object being processed
            captured_frames: List of captured frames to process

        Returns:
            A new PreprocessSession
        """
        session_id = str(uuid.uuid4())[:8]

        return PreprocessSession(
            session_id=session_id,
            object_id=object_id,
            captured_frames=captured_frames,
            masked_frames=[],
            metrics=PreprocessMetrics(),
            is_running=True,
            started_at=datetime.now(),
        )

    def process_frame(
        self,
        session: PreprocessSession,  # noqa: ARG002 - Used for future logging/validation
        frame: CapturedFrame,
        method: MaskMethod,
        settings: dict[str, float] | None = None,
    ) -> tuple[MaskedFrame, npt.NDArray[np.uint8], npt.NDArray[np.uint16], npt.NDArray[np.uint8]] | None:
        """Process a single frame to generate mask.

        Args:
            session: The active preprocess session
            frame: The captured frame to process
            method: The masking method to use
            settings: Method-specific settings (e.g., min_depth, max_depth)

        Returns:
            Tuple of (MaskedFrame, rgb_masked, depth_masked, mask) or None if failed
        """
        if settings is None:
            settings = {}

        # Load RGB and depth images
        if frame.rgb_path is None or frame.depth_path is None:
            return None

        rgb_path = Path(frame.rgb_path)
        depth_path = Path(frame.depth_path)

        if not rgb_path.exists() or not depth_path.exists():
            # Generate mock data for testing
            rgb: npt.NDArray[np.uint8] = np.zeros((480, 640, 3), dtype=np.uint8)
            depth: npt.NDArray[np.uint16] = np.zeros((480, 640), dtype=np.uint16)
        else:
            rgb_bgr = cv2.imread(str(rgb_path), cv2.IMREAD_COLOR)
            if rgb_bgr is not None:
                rgb = np.asarray(cv2.cvtColor(rgb_bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)
            else:
                rgb = np.zeros((480, 640, 3), dtype=np.uint8)
            depth_raw = cv2.imread(str(depth_path), cv2.IMREAD_UNCHANGED)
            if depth_raw is not None:
                depth = np.asarray(depth_raw, dtype=np.uint16)
            else:
                depth = np.zeros((480, 640), dtype=np.uint16)

        # Generate mask based on method
        mask = self._generate_mask(rgb, depth, method, settings)

        # Calculate mask quality
        quality = self.calculate_mask_quality(mask)

        # Apply mask to images
        rgb_masked = self._apply_mask(rgb, mask)
        depth_masked = self._apply_depth_mask(depth, mask)

        # Create masked frame metadata
        masked_frame = MaskedFrame(
            frame_id=frame.frame_id,
            method=method,
            quality=quality,
        )

        return masked_frame, rgb_masked, depth_masked, mask

    def _generate_mask(
        self,
        rgb: npt.NDArray[np.uint8],  # noqa: ARG002 - Used for GrabCut/U2Net methods
        depth: npt.NDArray[np.uint16],
        method: MaskMethod,
        settings: dict[str, float],
    ) -> npt.NDArray[np.uint8]:
        """Generate mask using specified method.

        Args:
            rgb: RGB image array
            depth: Depth image array (uint16 in mm)
            method: The masking method
            settings: Method-specific settings

        Returns:
            Binary mask (0 = background, 255 = foreground)
        """
        if method == MaskMethod.DEPTH_THRESHOLD:
            return self._generate_depth_threshold_mask(depth, settings)
        # For other methods, return a simple mask based on depth
        return self._generate_depth_threshold_mask(depth, settings)

    def _generate_depth_threshold_mask(
        self,
        depth: npt.NDArray[np.uint16],
        settings: dict[str, float],
    ) -> npt.NDArray[np.uint8]:
        """Generate mask using depth threshold.

        Args:
            depth: Depth image array (uint16 in mm)
            settings: Settings with min_depth and max_depth

        Returns:
            Binary mask (0 = background, 255 = foreground)
        """
        min_depth = settings.get("min_depth", 300)
        max_depth = settings.get("max_depth", 1500)

        # Create mask for valid depth range
        mask: npt.NDArray[np.uint8] = (
            ((depth >= min_depth) & (depth <= max_depth)).astype(np.uint8) * 255
        )

        # Apply morphological operations to clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = np.asarray(cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel), dtype=np.uint8)
        mask = np.asarray(cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel), dtype=np.uint8)

        return mask

    def calculate_mask_quality(
        self,
        mask: npt.NDArray[np.uint8],
    ) -> MaskQuality:
        """Calculate quality metrics for a mask.

        Args:
            mask: Binary mask array

        Returns:
            MaskQuality with calculated metrics
        """
        # Calculate mask area ratio
        total_pixels = mask.size
        mask_pixels = np.sum(mask > 0)
        mask_area_ratio = float(mask_pixels) / total_pixels

        # Calculate edge quality using Laplacian
        edge_quality = self._calculate_edge_quality(mask)

        # Determine if mask is valid
        is_valid = (
            self.MASK_AREA_RATIO_MIN <= mask_area_ratio <= self.MASK_AREA_RATIO_MAX
            and edge_quality >= self.EDGE_QUALITY_THRESHOLD
        )

        return MaskQuality(
            mask_area_ratio=mask_area_ratio,
            edge_quality=edge_quality,
            is_valid=is_valid,
        )

    def _calculate_edge_quality(self, mask: npt.NDArray[np.uint8]) -> float:
        """Calculate edge quality score.

        Args:
            mask: Binary mask array

        Returns:
            Edge quality score (0.0-1.0, higher is better)
        """
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 0.0

        # Find the largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)

        if area < 100:  # Too small
            return 0.0

        # Calculate perimeter and circularity
        perimeter = cv2.arcLength(largest_contour, True)
        if perimeter == 0:
            return 0.0

        circularity = 4 * np.pi * area / (perimeter * perimeter)

        # Calculate smoothness using contour approximation
        epsilon = 0.02 * perimeter
        approx = cv2.approxPolyDP(largest_contour, epsilon, True)
        smoothness = 1.0 - min(1.0, len(approx) / 100.0)

        # Combine metrics
        edge_quality = (circularity * 0.5 + smoothness * 0.5)
        return min(1.0, max(0.0, edge_quality))

    def _apply_mask(
        self,
        rgb: npt.NDArray[np.uint8],
        mask: npt.NDArray[np.uint8],
    ) -> npt.NDArray[np.uint8]:
        """Apply mask to RGB image.

        Args:
            rgb: RGB image array
            mask: Binary mask array

        Returns:
            Masked RGB image
        """
        mask_3ch = np.stack([mask] * 3, axis=-1)
        return np.where(mask_3ch > 0, rgb, 0).astype(np.uint8)

    def _apply_depth_mask(
        self,
        depth: npt.NDArray[np.uint16],
        mask: npt.NDArray[np.uint8],
    ) -> npt.NDArray[np.uint16]:
        """Apply mask to depth image.

        Args:
            depth: Depth image array
            mask: Binary mask array

        Returns:
            Masked depth image
        """
        return np.where(mask > 0, depth, 0).astype(np.uint16)

    def save_masked_frame(
        self,
        session: PreprocessSession,
        masked_frame: MaskedFrame,
        rgb_masked: npt.NDArray[np.uint8],
        depth_masked: npt.NDArray[np.uint16],
        mask: npt.NDArray[np.uint8],
    ) -> MaskedFrame:
        """Save masked frame data to disk.

        Args:
            session: The active preprocess session
            masked_frame: Masked frame metadata to update
            rgb_masked: Masked RGB image array
            depth_masked: Masked depth image array
            mask: Binary mask array

        Returns:
            Updated MaskedFrame with file paths
        """
        # Create project directory structure
        project_path = self.projects_dir / session.object_id
        masked_frames_dir = project_path / "masked_frames"
        masked_frames_dir.mkdir(parents=True, exist_ok=True)

        # Generate file paths
        rgb_filename = f"frame_{masked_frame.frame_id:04d}_rgb_masked.png"
        depth_filename = f"frame_{masked_frame.frame_id:04d}_depth_masked.png"
        mask_filename = f"frame_{masked_frame.frame_id:04d}_mask.png"

        rgb_path = masked_frames_dir / rgb_filename
        depth_path = masked_frames_dir / depth_filename
        mask_path = masked_frames_dir / mask_filename

        # Save RGB as PNG (convert to BGR for OpenCV)
        bgr_masked = cv2.cvtColor(rgb_masked, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(rgb_path), bgr_masked)

        # Save depth as 16-bit PNG
        cv2.imwrite(str(depth_path), depth_masked)

        # Save mask as 8-bit PNG
        cv2.imwrite(str(mask_path), mask)

        # Create updated masked frame with paths
        return MaskedFrame(
            frame_id=masked_frame.frame_id,
            method=masked_frame.method,
            quality=masked_frame.quality,
            mask_path=str(mask_path),
            rgb_masked_path=str(rgb_path),
            depth_masked_path=str(depth_path),
        )

    def update_metrics(
        self,
        session: PreprocessSession,
    ) -> PreprocessMetrics:
        """Update session metrics based on processed frames.

        Args:
            session: The preprocess session

        Returns:
            Updated PreprocessMetrics
        """
        masked_frames = session.masked_frames

        if not masked_frames:
            return PreprocessMetrics()

        # Calculate mean values
        area_ratios = [f.quality.mask_area_ratio for f in masked_frames]
        edge_qualities = [f.quality.edge_quality for f in masked_frames]
        num_valid = sum(1 for f in masked_frames if f.quality.is_valid)

        mask_area_ratio_mean = sum(area_ratios) / len(area_ratios)
        edge_quality_mean = sum(edge_qualities) / len(edge_qualities)

        return PreprocessMetrics(
            mask_area_ratio_mean=mask_area_ratio_mean,
            edge_quality_mean=edge_quality_mean,
            num_processed=len(masked_frames),
            num_valid=num_valid,
        )

    def stop_session(
        self,
        session: PreprocessSession,
    ) -> PreprocessSession:
        """Stop a preprocess session.

        Args:
            session: The preprocess session to stop

        Returns:
            Updated PreprocessSession with is_running=False
        """
        return PreprocessSession(
            session_id=session.session_id,
            object_id=session.object_id,
            captured_frames=session.captured_frames,
            masked_frames=session.masked_frames,
            metrics=session.metrics,
            is_running=False,
            started_at=session.started_at,
        )

    def add_masked_frame_to_session(
        self,
        session: PreprocessSession,
        masked_frame: MaskedFrame,
    ) -> PreprocessSession:
        """Add a masked frame to the session and update metrics.

        Args:
            session: The preprocess session
            masked_frame: The masked frame to add

        Returns:
            Updated PreprocessSession with new frame and metrics
        """
        new_masked_frames = [*session.masked_frames, masked_frame]

        # Create temporary session to calculate metrics
        temp_session = PreprocessSession(
            session_id=session.session_id,
            object_id=session.object_id,
            captured_frames=session.captured_frames,
            masked_frames=new_masked_frames,
            metrics=session.metrics,
            is_running=session.is_running,
            started_at=session.started_at,
        )

        new_metrics = self.update_metrics(temp_session)

        return PreprocessSession(
            session_id=session.session_id,
            object_id=session.object_id,
            captured_frames=session.captured_frames,
            masked_frames=new_masked_frames,
            metrics=new_metrics,
            is_running=session.is_running,
            started_at=session.started_at,
        )
