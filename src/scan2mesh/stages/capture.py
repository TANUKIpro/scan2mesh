"""RGBD capture stage.

This module provides the RGBDCapture class for capturing depth and color frames.
"""

import contextlib
from pathlib import Path
from time import time

import numpy as np

from scan2mesh.exceptions import CameraError, CaptureError
from scan2mesh.models import (
    CaptureMetrics,
    CapturePlan,
    FrameData,
    FrameQuality,
    FramesMetadata,
    RawFrame,
)
from scan2mesh.services import BaseCameraService, ImageService, StorageService


class RGBDCapture:
    """Capture RGBD frames using RealSense camera.

    This stage handles:
    - Camera initialization and configuration
    - Frame capture with depth alignment
    - Quality assessment during capture
    - Frame storage with metadata

    Attributes:
        project_dir: Path to the project directory
        storage: Storage service instance
        image_service: Image analysis service
        camera: Camera service instance
    """

    # Quality thresholds for frame evaluation
    MIN_BLUR_SCORE = 0.3
    MIN_DEPTH_VALID_RATIO = 0.5
    MIN_OBJECT_OCCUPANCY = 0.1
    KEYFRAME_BLUR_THRESHOLD = 0.5
    KEYFRAME_DEPTH_THRESHOLD = 0.7

    def __init__(
        self,
        project_dir: Path,
        camera: BaseCameraService | None = None,
        storage: StorageService | None = None,
        image_service: ImageService | None = None,
    ) -> None:
        """Initialize RGBDCapture.

        Args:
            project_dir: Path to the project directory
            camera: Camera service instance (optional)
            storage: Storage service instance (optional)
            image_service: Image analysis service instance (optional)
        """
        self.project_dir = project_dir
        self.storage = storage or StorageService(project_dir)
        self.image_service = image_service or ImageService()
        self._camera = camera
        self._is_capturing = False
        self._frames: list[FrameData] = []
        self._raw_frames: list[RawFrame] = []
        self._start_time: float | None = None
        self._frame_count = 0
        self._capture_plan: CapturePlan | None = None

    @property
    def camera(self) -> BaseCameraService:
        """Get camera service, raising error if not set."""
        if self._camera is None:
            raise CaptureError("Camera not initialized. Call start_capture() first.")
        return self._camera

    def set_camera(self, camera: BaseCameraService) -> None:
        """Set the camera service.

        Args:
            camera: Camera service instance
        """
        self._camera = camera

    def start_capture(self, plan: CapturePlan | None = None) -> None:
        """Start the capture session.

        Args:
            plan: Optional capture plan to follow

        Raises:
            CaptureError: If capture is already in progress or camera not set
            CameraError: If camera fails to start
        """
        if self._is_capturing:
            raise CaptureError("Capture session already in progress")

        if self._camera is None:
            raise CaptureError("Camera not set. Call set_camera() first.")

        self._capture_plan = plan
        self._frames = []
        self._raw_frames = []
        self._frame_count = 0
        self._start_time = time()

        try:
            self._camera.start_streaming()
            self._is_capturing = True
        except CameraError:
            raise
        except Exception as e:
            raise CaptureError(f"Failed to start capture: {e}") from e

    def capture_frame(self) -> tuple[FrameData, FrameQuality]:
        """Capture a single RGBD frame.

        Returns:
            Tuple of (FrameData, FrameQuality)

        Raises:
            CaptureError: If capture is not in progress
            CameraError: If frame capture fails
        """
        if not self._is_capturing:
            raise CaptureError("Capture session not started. Call start_capture() first.")

        # Capture raw frame from camera
        raw_frame = self.camera.capture_frame()

        # Evaluate frame quality
        quality = self.evaluate_quality(raw_frame)

        # Save frame data to storage
        rgb_path, depth_path = self.storage.save_frame_data(
            self._frame_count,
            raw_frame.rgb,
            raw_frame.depth,
        )

        # Create frame data
        frame_data = FrameData(
            frame_id=self._frame_count,
            timestamp=raw_frame.timestamp,
            rgb_path=rgb_path,
            depth_path=depth_path,
            intrinsics=raw_frame.intrinsics,
            quality=quality,
        )

        # Store for later processing
        self._frames.append(frame_data)
        self._raw_frames.append(raw_frame)
        self._frame_count += 1

        return frame_data, quality

    def evaluate_quality(self, frame: RawFrame) -> FrameQuality:
        """Evaluate quality of a captured frame.

        Args:
            frame: Raw frame to evaluate

        Returns:
            FrameQuality with quality metrics
        """
        blur_score = self.image_service.calculate_blur_score(frame.rgb)
        depth_valid_ratio = self.image_service.calculate_depth_valid_ratio(frame.depth)
        object_occupancy = self.image_service.estimate_object_occupancy(frame.depth)

        # Determine if this frame qualifies as a keyframe
        is_keyframe = (
            blur_score >= self.KEYFRAME_BLUR_THRESHOLD
            and depth_valid_ratio >= self.KEYFRAME_DEPTH_THRESHOLD
            and object_occupancy >= self.MIN_OBJECT_OCCUPANCY
        )

        return FrameQuality(
            depth_valid_ratio=depth_valid_ratio,
            blur_score=blur_score,
            object_occupancy=object_occupancy,
            is_keyframe=is_keyframe,
        )

    def _select_keyframes(self) -> list[int]:
        """Select keyframes from captured frames.

        Returns:
            List of frame IDs selected as keyframes
        """
        keyframe_ids = []

        for frame in self._frames:
            if frame.quality.is_keyframe:
                keyframe_ids.append(frame.frame_id)

        return keyframe_ids

    def estimate_coverage(self) -> float:
        """Estimate viewpoint coverage uniformity.

        Returns:
            Coverage score (0.0-1.0)
        """
        if not self._frames:
            return 0.0

        # Simple coverage estimation based on keyframe count and distribution
        # For a proper implementation, this would analyze viewpoint angles
        keyframes = [f for f in self._frames if f.quality.is_keyframe]

        if not keyframes:
            return 0.0

        # Basic heuristic: coverage based on keyframe count vs planned viewpoints
        if self._capture_plan:
            expected_viewpoints = len(self._capture_plan.viewpoints)
            if expected_viewpoints > 0:
                coverage = min(1.0, len(keyframes) / expected_viewpoints)
                return coverage

        # Without a plan, assume coverage based on frame quality
        quality_scores = [
            f.quality.blur_score * f.quality.depth_valid_ratio * f.quality.object_occupancy
            for f in keyframes
        ]

        return min(1.0, sum(quality_scores) / max(len(keyframes), 1))

    def stop_capture(self) -> CaptureMetrics:
        """Stop the capture session and generate metrics.

        Returns:
            CaptureMetrics summarizing the capture session

        Raises:
            CaptureError: If capture is not in progress
        """
        if not self._is_capturing:
            raise CaptureError("Capture session not started")

        # Stop camera streaming
        with contextlib.suppress(Exception):
            self.camera.stop_streaming()

        self._is_capturing = False

        # Calculate capture duration
        capture_duration = time() - self._start_time if self._start_time else 0.0

        # Select keyframes
        keyframe_ids = self._select_keyframes()

        # Calculate metrics
        keyframes = [f for f in self._frames if f.frame_id in keyframe_ids]

        if keyframes:
            depth_ratios = [f.quality.depth_valid_ratio for f in keyframes]
            blur_scores = [f.quality.blur_score for f in keyframes]

            depth_valid_ratio_mean = float(np.mean(depth_ratios))
            depth_valid_ratio_min = float(np.min(depth_ratios))
            blur_score_mean = float(np.mean(blur_scores))
            blur_score_min = float(np.min(blur_scores))
        else:
            depth_valid_ratio_mean = 0.0
            depth_valid_ratio_min = 0.0
            blur_score_mean = 0.0
            blur_score_min = 0.0

        coverage_score = self.estimate_coverage()

        # Create metrics
        metrics = CaptureMetrics(
            num_frames_raw=self._frame_count,
            num_keyframes=len(keyframe_ids),
            depth_valid_ratio_mean=depth_valid_ratio_mean,
            depth_valid_ratio_min=depth_valid_ratio_min,
            blur_score_mean=blur_score_mean,
            blur_score_min=blur_score_min,
            coverage_score=coverage_score,
            capture_duration_sec=capture_duration,
            gate_status="pending",
            gate_reasons=[],
        )

        # Save metadata and metrics
        frames_metadata = FramesMetadata(
            frames=self._frames,
            total_frames=self._frame_count,
            keyframe_ids=keyframe_ids,
        )

        self.storage.save_frames_metadata(frames_metadata)
        self.storage.save_capture_metrics(metrics)

        return metrics

    def get_frame_count(self) -> int:
        """Get the number of captured frames.

        Returns:
            Number of frames captured
        """
        return self._frame_count

    def get_keyframe_count(self) -> int:
        """Get the number of keyframes.

        Returns:
            Number of keyframes
        """
        return len([f for f in self._frames if f.quality.is_keyframe])

    def is_capturing(self) -> bool:
        """Check if capture is in progress.

        Returns:
            True if capturing, False otherwise
        """
        return self._is_capturing
