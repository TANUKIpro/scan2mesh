"""RGBD capture stage.

This module provides the RGBDCapture class for capturing depth and color frames.
"""

from pathlib import Path

from scan2mesh.exceptions import NotImplementedStageError


class RGBDCapture:
    """Capture RGBD frames using RealSense camera.

    This stage handles:
    - Camera initialization and configuration
    - Frame capture with depth alignment
    - Quality assessment during capture
    - Frame storage with metadata

    Attributes:
        project_dir: Path to the project directory
    """

    def __init__(self, project_dir: Path) -> None:
        """Initialize RGBDCapture.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir

    def start_capture(self) -> None:
        """Start the capture session.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("RGBDCapture.start_capture")

    def capture_frame(self) -> None:
        """Capture a single RGBD frame.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("RGBDCapture.capture_frame")

    def stop_capture(self) -> None:
        """Stop the capture session.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("RGBDCapture.stop_capture")
