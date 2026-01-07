"""Capture service for managing capture sessions."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import ClassVar

import cv2
import numpy as np
import numpy.typing as npt

from scan2mesh_gui.models.capture_session import (
    CapturedFrame,
    CaptureSession,
    CaptureSessionMetrics,
    FrameQuality,
)
from scan2mesh_gui.services.device_service import DeviceService


class CaptureService:
    """Service for managing capture sessions and frame processing."""

    # Quality thresholds for keyframe detection
    DEPTH_VALID_THRESHOLD: ClassVar[float] = 0.6
    BLUR_SCORE_THRESHOLD: ClassVar[float] = 0.5

    def __init__(self, projects_dir: Path) -> None:
        """Initialize the capture service.

        Args:
            projects_dir: Base directory for project data
        """
        self.projects_dir = projects_dir
        self._device_service = DeviceService()

    def start_session(
        self,
        object_id: str,
        target_keyframes: int,
    ) -> CaptureSession:
        """Start a new capture session.

        Args:
            object_id: ID of the object being scanned
            target_keyframes: Target number of frames to capture

        Returns:
            A new CaptureSession
        """
        session_id = str(uuid.uuid4())[:8]

        return CaptureSession(
            session_id=session_id,
            object_id=object_id,
            target_keyframes=target_keyframes,
            frames=[],
            metrics=CaptureSessionMetrics(),
            is_running=True,
            started_at=datetime.now(),
        )

    def capture_frame(
        self,
        session: CaptureSession,
    ) -> tuple[CapturedFrame, npt.NDArray[np.uint8], npt.NDArray[np.uint16]] | None:
        """Capture a single frame.

        Args:
            session: The active capture session

        Returns:
            Tuple of (CapturedFrame, rgb, depth) or None if capture failed
        """
        # Get the selected device
        device = self._device_service.get_selected_device()
        if device is None:
            devices = self._device_service.list_devices()
            if not devices:
                return None
            device = devices[0]

        # Capture frame from device
        result = self._device_service.test_capture(device.serial_number)
        if result is None:
            return None

        rgb, depth = result

        # Calculate frame quality
        quality = self.calculate_quality(rgb, depth)

        # Create frame metadata
        frame_id = len(session.frames)
        frame = CapturedFrame(
            frame_id=frame_id,
            timestamp=datetime.now(),
            quality=quality,
        )

        return frame, rgb, depth

    def calculate_quality(
        self,
        rgb: npt.NDArray[np.uint8],
        depth: npt.NDArray[np.uint16],
    ) -> FrameQuality:
        """Calculate quality metrics for a frame.

        Args:
            rgb: RGB image array
            depth: Depth image array (uint16 in mm)

        Returns:
            FrameQuality with calculated metrics
        """
        # Calculate depth valid ratio
        valid_depth = depth > 0
        depth_valid_ratio = float(np.sum(valid_depth)) / depth.size

        # Calculate blur score using Laplacian variance
        blur_score = self._calculate_blur_score(rgb)

        # Determine if this is a keyframe
        is_keyframe = (
            depth_valid_ratio >= self.DEPTH_VALID_THRESHOLD
            and blur_score >= self.BLUR_SCORE_THRESHOLD
        )

        return FrameQuality(
            depth_valid_ratio=depth_valid_ratio,
            blur_score=blur_score,
            is_keyframe=is_keyframe,
        )

    def _calculate_blur_score(self, rgb: npt.NDArray[np.uint8]) -> float:
        """Calculate blur score using Laplacian variance.

        Args:
            rgb: RGB image array

        Returns:
            Blur score (0.0-1.0, higher is sharper)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY) if len(rgb.shape) == 3 else rgb

        # Calculate Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = float(laplacian.var())

        # Normalize to 0-1 range (empirical thresholds: <100 = blurry, >500 = sharp)
        score = min(1.0, max(0.0, (variance - 100) / 400))

        return score

    def save_frame(
        self,
        session: CaptureSession,
        frame: CapturedFrame,
        rgb: npt.NDArray[np.uint8],
        depth: npt.NDArray[np.uint16],
    ) -> CapturedFrame:
        """Save frame data to disk.

        Args:
            session: The active capture session
            frame: Frame metadata to update
            rgb: RGB image array
            depth: Depth image array

        Returns:
            Updated CapturedFrame with file paths
        """
        # Create project directory structure
        project_path = self.projects_dir / session.object_id
        raw_frames_dir = project_path / "raw_frames"
        raw_frames_dir.mkdir(parents=True, exist_ok=True)

        # Generate file paths
        rgb_filename = f"frame_{frame.frame_id:04d}_rgb.png"
        depth_filename = f"frame_{frame.frame_id:04d}_depth.png"

        rgb_path = raw_frames_dir / rgb_filename
        depth_path = raw_frames_dir / depth_filename

        # Save RGB as PNG
        # Convert RGB to BGR for OpenCV
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(rgb_path), bgr)

        # Save depth as 16-bit PNG
        cv2.imwrite(str(depth_path), depth)

        # Create updated frame with paths
        return CapturedFrame(
            frame_id=frame.frame_id,
            timestamp=frame.timestamp,
            quality=frame.quality,
            rgb_path=str(rgb_path),
            depth_path=str(depth_path),
        )

    def update_metrics(
        self,
        session: CaptureSession,
    ) -> CaptureSessionMetrics:
        """Update session metrics based on captured frames.

        Args:
            session: The capture session

        Returns:
            Updated CaptureSessionMetrics
        """
        frames = session.frames

        if not frames:
            return CaptureSessionMetrics()

        # Calculate mean values
        depth_ratios = [f.quality.depth_valid_ratio for f in frames]
        blur_scores = [f.quality.blur_score for f in frames]
        num_keyframes = sum(1 for f in frames if f.quality.is_keyframe)

        depth_valid_ratio_mean = sum(depth_ratios) / len(depth_ratios)
        blur_score_mean = sum(blur_scores) / len(blur_scores)

        # Calculate coverage score based on progress
        # In mock mode, coverage increases with frame count
        coverage_score = min(1.0, len(frames) / session.target_keyframes) * 0.9

        return CaptureSessionMetrics(
            depth_valid_ratio_mean=depth_valid_ratio_mean,
            blur_score_mean=blur_score_mean,
            coverage_score=coverage_score,
            num_frames=len(frames),
            num_keyframes=num_keyframes,
        )

    def stop_session(
        self,
        session: CaptureSession,
    ) -> CaptureSession:
        """Stop a capture session.

        Args:
            session: The capture session to stop

        Returns:
            Updated CaptureSession with is_running=False
        """
        return CaptureSession(
            session_id=session.session_id,
            object_id=session.object_id,
            target_keyframes=session.target_keyframes,
            frames=session.frames,
            metrics=session.metrics,
            is_running=False,
            started_at=session.started_at,
        )

    def add_frame_to_session(
        self,
        session: CaptureSession,
        frame: CapturedFrame,
    ) -> CaptureSession:
        """Add a frame to the session and update metrics.

        Args:
            session: The capture session
            frame: The frame to add

        Returns:
            Updated CaptureSession with new frame and metrics
        """
        new_frames = [*session.frames, frame]

        # Create temporary session to calculate metrics
        temp_session = CaptureSession(
            session_id=session.session_id,
            object_id=session.object_id,
            target_keyframes=session.target_keyframes,
            frames=new_frames,
            metrics=session.metrics,
            is_running=session.is_running,
            started_at=session.started_at,
        )

        new_metrics = self.update_metrics(temp_session)

        return CaptureSession(
            session_id=session.session_id,
            object_id=session.object_id,
            target_keyframes=session.target_keyframes,
            frames=new_frames,
            metrics=new_metrics,
            is_running=session.is_running,
            started_at=session.started_at,
        )
