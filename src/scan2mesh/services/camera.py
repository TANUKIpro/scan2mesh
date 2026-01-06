"""Camera service for RealSense camera control.

This module provides camera services for capturing RGBD frames.
It includes both a real RealSense implementation and a mock implementation for testing.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

from scan2mesh.exceptions import CameraError
from scan2mesh.models import CameraIntrinsics, RawFrame


class CameraServiceProtocol(Protocol):
    """Protocol for camera services."""

    def start_streaming(self) -> None:
        """Start the camera stream."""
        ...

    def stop_streaming(self) -> None:
        """Stop the camera stream."""
        ...

    def capture_frame(self) -> RawFrame:
        """Capture a single RGBD frame."""
        ...

    def get_intrinsics(self) -> CameraIntrinsics:
        """Get camera intrinsic parameters."""
        ...

    def get_depth_scale(self) -> float:
        """Get depth scale (meters per depth unit)."""
        ...

    @property
    def is_streaming(self) -> bool:
        """Check if camera is currently streaming."""
        ...


class BaseCameraService(ABC):
    """Base class for camera services.

    Provides common functionality and interface for camera operations.
    """

    def __init__(self) -> None:
        """Initialize base camera service."""
        self._is_streaming = False

    @property
    def is_streaming(self) -> bool:
        """Check if camera is currently streaming."""
        return self._is_streaming

    @abstractmethod
    def start_streaming(self) -> None:
        """Start the camera stream."""
        ...

    @abstractmethod
    def stop_streaming(self) -> None:
        """Stop the camera stream."""
        ...

    @abstractmethod
    def capture_frame(self) -> RawFrame:
        """Capture a single RGBD frame."""
        ...

    @abstractmethod
    def get_intrinsics(self) -> CameraIntrinsics:
        """Get camera intrinsic parameters."""
        ...

    @abstractmethod
    def get_depth_scale(self) -> float:
        """Get depth scale (meters per depth unit)."""
        ...

    def __enter__(self) -> "BaseCameraService":
        """Context manager entry."""
        self.start_streaming()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit."""
        self.stop_streaming()


class MockCameraService(BaseCameraService):
    """Mock camera service for testing and development.

    Generates synthetic RGBD frames with configurable parameters.
    """

    # Default resolution matching RealSense D435
    DEFAULT_RGB_WIDTH = 1920
    DEFAULT_RGB_HEIGHT = 1080
    DEFAULT_DEPTH_WIDTH = 1280
    DEFAULT_DEPTH_HEIGHT = 720
    DEFAULT_DEPTH_SCALE = 0.001  # 1mm per depth unit

    def __init__(
        self,
        rgb_width: int = DEFAULT_RGB_WIDTH,
        rgb_height: int = DEFAULT_RGB_HEIGHT,
        depth_width: int = DEFAULT_DEPTH_WIDTH,
        depth_height: int = DEFAULT_DEPTH_HEIGHT,
        depth_scale: float = DEFAULT_DEPTH_SCALE,
        seed: int | None = None,
    ) -> None:
        """Initialize MockCameraService.

        Args:
            rgb_width: RGB image width
            rgb_height: RGB image height
            depth_width: Depth image width
            depth_height: Depth image height
            depth_scale: Depth scale (meters per depth unit)
            seed: Random seed for reproducible frames
        """
        super().__init__()
        self._rgb_width = rgb_width
        self._rgb_height = rgb_height
        self._depth_width = depth_width
        self._depth_height = depth_height
        self._depth_scale = depth_scale
        self._rng = np.random.default_rng(seed)
        self._frame_count = 0

    def start_streaming(self) -> None:
        """Start the mock camera stream."""
        if self._is_streaming:
            return
        self._is_streaming = True
        self._frame_count = 0

    def stop_streaming(self) -> None:
        """Stop the mock camera stream."""
        self._is_streaming = False

    def capture_frame(self) -> RawFrame:
        """Capture a synthetic RGBD frame.

        Returns:
            RawFrame with generated RGB and depth data

        Raises:
            CameraError: If camera is not streaming
        """
        if not self._is_streaming:
            raise CameraError("Camera is not streaming. Call start_streaming() first.")

        # Generate synthetic RGB image with some pattern
        rgb = self._generate_rgb()

        # Generate synthetic depth image with object in center
        depth = self._generate_depth()

        self._frame_count += 1

        return RawFrame(
            rgb=rgb,
            depth=depth,
            timestamp=datetime.now(),
            intrinsics=self.get_intrinsics(),
        )

    def _generate_rgb(self) -> NDArray[np.uint8]:
        """Generate synthetic RGB image.

        Creates an image with a colored sphere-like pattern in the center.
        """
        rgb = np.zeros((self._rgb_height, self._rgb_width, 3), dtype=np.uint8)

        # Create background with slight noise
        rgb[:, :, 0] = 50  # Dark blue background
        rgb[:, :, 1] = 50
        rgb[:, :, 2] = 80

        # Add centered "object" (sphere-like pattern)
        center_y = self._rgb_height // 2
        center_x = self._rgb_width // 2
        radius = min(self._rgb_height, self._rgb_width) // 4

        y_coords, x_coords = np.ogrid[: self._rgb_height, : self._rgb_width]
        dist_from_center = np.sqrt(
            (x_coords - center_x) ** 2 + (y_coords - center_y) ** 2
        )

        # Object mask
        object_mask = dist_from_center < radius

        # Color the object based on angle (to simulate texture)
        angle = np.arctan2(y_coords - center_y, x_coords - center_x)
        object_color = (np.sin(angle * 3 + self._frame_count * 0.1) * 50 + 200).astype(
            np.uint8
        )

        rgb[object_mask, 0] = 180  # Orange-ish object
        rgb[object_mask, 1] = 100
        rgb[object_mask, 2] = object_color[object_mask]

        # Add some noise
        noise = self._rng.integers(0, 10, (self._rgb_height, self._rgb_width, 3), dtype=np.uint8)
        result: NDArray[np.uint8] = np.clip(
            rgb.astype(np.int16) + noise.astype(np.int16), 0, 255
        ).astype(np.uint8)

        return result

    def _generate_depth(self) -> NDArray[np.uint16]:
        """Generate synthetic depth image.

        Creates depth data with an object in the center at ~500mm.
        """
        depth = np.zeros((self._depth_height, self._depth_width), dtype=np.uint16)

        # Background at ~1500mm
        depth[:, :] = 1500

        # Object in center at ~400-600mm
        center_y = self._depth_height // 2
        center_x = self._depth_width // 2
        radius = min(self._depth_height, self._depth_width) // 4

        y_coords, x_coords = np.ogrid[: self._depth_height, : self._depth_width]
        dist_from_center = np.sqrt(
            (x_coords - center_x) ** 2 + (y_coords - center_y) ** 2
        )

        # Object mask
        object_mask = dist_from_center < radius

        # Create sphere-like depth (closer in center)
        normalized_dist = dist_from_center[object_mask] / radius
        sphere_depth = 500 - (1 - normalized_dist**2) * 100  # 400-500mm range
        depth[object_mask] = sphere_depth.astype(np.uint16)

        # Add some invalid pixels (holes) randomly
        hole_mask = self._rng.random((self._depth_height, self._depth_width)) < 0.02
        depth[hole_mask] = 0

        return depth

    def get_intrinsics(self) -> CameraIntrinsics:
        """Get camera intrinsic parameters.

        Returns mock intrinsics similar to RealSense D435.
        """
        # Approximated D435 depth intrinsics
        return CameraIntrinsics(
            width=self._depth_width,
            height=self._depth_height,
            fx=640.0,  # Focal length x
            fy=640.0,  # Focal length y
            cx=self._depth_width / 2,  # Principal point x
            cy=self._depth_height / 2,  # Principal point y
            depth_scale=self._depth_scale,
        )

    def get_depth_scale(self) -> float:
        """Get depth scale (meters per depth unit)."""
        return self._depth_scale


class RealSenseCameraService(BaseCameraService):
    """RealSense camera service using pyrealsense2.

    Provides real camera control for Intel RealSense D400 series cameras.
    """

    def __init__(self, device_id: int = 0) -> None:
        """Initialize RealSenseCameraService.

        Args:
            device_id: Device index for multiple cameras (default: 0)

        Raises:
            CameraError: If pyrealsense2 is not available
        """
        super().__init__()
        self._device_id = device_id
        self._pipeline: Any = None
        self._profile: Any = None
        self._depth_scale: float = 0.001
        self._rs: Any = None

        # Try to import pyrealsense2
        try:
            import pyrealsense2 as rs

            self._rs = rs
        except ImportError as e:
            raise CameraError(
                "pyrealsense2 is not installed. "
                "Install it with: pip install pyrealsense2"
            ) from e

    def start_streaming(self) -> None:
        """Start the RealSense camera stream.

        Raises:
            CameraError: If camera cannot be started
        """
        if self._is_streaming:
            return

        try:
            self._pipeline = self._rs.pipeline()
            config = self._rs.config()

            # Enable streams
            config.enable_stream(
                self._rs.stream.depth, 1280, 720, self._rs.format.z16, 30
            )
            config.enable_stream(
                self._rs.stream.color, 1920, 1080, self._rs.format.bgr8, 30
            )

            # Start pipeline
            self._profile = self._pipeline.start(config)

            # Get depth scale
            depth_sensor = self._profile.get_device().first_depth_sensor()
            self._depth_scale = depth_sensor.get_depth_scale()

            self._is_streaming = True

        except Exception as e:
            self._pipeline = None
            self._profile = None
            raise CameraError(f"Failed to start RealSense camera: {e}") from e

    def stop_streaming(self) -> None:
        """Stop the RealSense camera stream."""
        import contextlib

        if self._pipeline and self._is_streaming:
            with contextlib.suppress(Exception):
                self._pipeline.stop()
        self._pipeline = None
        self._profile = None
        self._is_streaming = False

    def capture_frame(self) -> RawFrame:
        """Capture an RGBD frame from RealSense camera.

        Returns:
            RawFrame with camera data

        Raises:
            CameraError: If frame capture fails
        """
        if not self._is_streaming or self._pipeline is None:
            raise CameraError("Camera is not streaming. Call start_streaming() first.")

        try:
            # Wait for frames
            frames = self._pipeline.wait_for_frames()

            # Align depth to color
            align = self._rs.align(self._rs.stream.color)
            aligned_frames = align.process(frames)

            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

            if not depth_frame or not color_frame:
                raise CameraError("Failed to get frames from camera")

            # Convert to numpy arrays
            depth = np.asanyarray(depth_frame.get_data()).astype(np.uint16)
            rgb = np.asanyarray(color_frame.get_data()).astype(np.uint8)

            # BGR to RGB
            rgb = rgb[:, :, ::-1].copy()

            return RawFrame(
                rgb=rgb,
                depth=depth,
                timestamp=datetime.now(),
                intrinsics=self.get_intrinsics(),
            )

        except CameraError:
            raise
        except Exception as e:
            raise CameraError(f"Failed to capture frame: {e}") from e

    def get_intrinsics(self) -> CameraIntrinsics:
        """Get camera intrinsic parameters.

        Returns:
            CameraIntrinsics from the depth stream

        Raises:
            CameraError: If camera is not streaming
        """
        if not self._is_streaming or self._profile is None:
            raise CameraError("Camera is not streaming")

        try:
            depth_stream = self._profile.get_stream(self._rs.stream.depth)
            intrinsics = depth_stream.as_video_stream_profile().get_intrinsics()

            return CameraIntrinsics(
                width=intrinsics.width,
                height=intrinsics.height,
                fx=intrinsics.fx,
                fy=intrinsics.fy,
                cx=intrinsics.ppx,
                cy=intrinsics.ppy,
                depth_scale=self._depth_scale,
            )
        except Exception as e:
            raise CameraError(f"Failed to get intrinsics: {e}") from e

    def get_depth_scale(self) -> float:
        """Get depth scale (meters per depth unit)."""
        return self._depth_scale


def create_camera_service(use_mock: bool = False, **kwargs: object) -> BaseCameraService:
    """Factory function to create appropriate camera service.

    Args:
        use_mock: If True, create MockCameraService. Otherwise try RealSense.
        **kwargs: Additional arguments passed to the camera service constructor.

    Returns:
        Camera service instance

    Raises:
        CameraError: If RealSense is requested but not available
    """
    if use_mock:
        return MockCameraService(**kwargs)  # type: ignore[arg-type]

    # Try to create RealSense service
    try:
        return RealSenseCameraService(**kwargs)  # type: ignore[arg-type]
    except CameraError:
        # Fall back to mock if RealSense not available
        raise
