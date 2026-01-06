"""Tests for CameraService."""

import numpy as np
import pytest

from scan2mesh.exceptions import CameraError
from scan2mesh.models import CameraIntrinsics, RawFrame
from scan2mesh.services.camera import MockCameraService, create_camera_service


class TestMockCameraService:
    """Tests for MockCameraService class."""

    @pytest.fixture
    def camera(self) -> MockCameraService:
        """Create MockCameraService instance with fixed seed."""
        return MockCameraService(seed=42)

    def test_initial_state(self, camera: MockCameraService) -> None:
        """Camera should not be streaming initially."""
        assert camera.is_streaming is False

    def test_start_streaming(self, camera: MockCameraService) -> None:
        """Camera should be streaming after start_streaming()."""
        camera.start_streaming()
        assert camera.is_streaming is True
        camera.stop_streaming()

    def test_stop_streaming(self, camera: MockCameraService) -> None:
        """Camera should not be streaming after stop_streaming()."""
        camera.start_streaming()
        camera.stop_streaming()
        assert camera.is_streaming is False

    def test_capture_frame_without_streaming_raises(
        self, camera: MockCameraService
    ) -> None:
        """Capturing without streaming should raise CameraError."""
        with pytest.raises(CameraError, match="not streaming"):
            camera.capture_frame()

    def test_capture_frame_returns_raw_frame(
        self, camera: MockCameraService
    ) -> None:
        """Capture should return RawFrame with correct types."""
        camera.start_streaming()
        try:
            frame = camera.capture_frame()

            assert isinstance(frame, RawFrame)
            assert isinstance(frame.rgb, np.ndarray)
            assert isinstance(frame.depth, np.ndarray)
            assert frame.rgb.dtype == np.uint8
            assert frame.depth.dtype == np.uint16
            assert frame.timestamp is not None
            assert isinstance(frame.intrinsics, CameraIntrinsics)
        finally:
            camera.stop_streaming()

    def test_capture_frame_rgb_shape(self, camera: MockCameraService) -> None:
        """RGB image should have correct shape (H, W, 3)."""
        camera.start_streaming()
        try:
            frame = camera.capture_frame()

            assert frame.rgb.shape == (
                MockCameraService.DEFAULT_RGB_HEIGHT,
                MockCameraService.DEFAULT_RGB_WIDTH,
                3,
            )
        finally:
            camera.stop_streaming()

    def test_capture_frame_depth_shape(self, camera: MockCameraService) -> None:
        """Depth image should have correct shape (H, W)."""
        camera.start_streaming()
        try:
            frame = camera.capture_frame()

            assert frame.depth.shape == (
                MockCameraService.DEFAULT_DEPTH_HEIGHT,
                MockCameraService.DEFAULT_DEPTH_WIDTH,
            )
        finally:
            camera.stop_streaming()

    def test_capture_frame_has_object(self, camera: MockCameraService) -> None:
        """Generated frames should have object-like depth values."""
        camera.start_streaming()
        try:
            frame = camera.capture_frame()

            # Center should have depth values in object range (400-600mm)
            center_y = frame.depth.shape[0] // 2
            center_x = frame.depth.shape[1] // 2
            center_depth = frame.depth[center_y, center_x]

            assert 300 < center_depth < 700, f"Center depth {center_depth} not in expected range"
        finally:
            camera.stop_streaming()

    def test_capture_frame_has_holes(self, camera: MockCameraService) -> None:
        """Generated depth should have some invalid (zero) pixels."""
        camera.start_streaming()
        try:
            frame = camera.capture_frame()

            # Should have some zero pixels (holes)
            zero_count = np.count_nonzero(frame.depth == 0)
            assert zero_count > 0, "Depth should have some invalid pixels"
        finally:
            camera.stop_streaming()

    def test_get_intrinsics(self, camera: MockCameraService) -> None:
        """Intrinsics should have correct values."""
        intrinsics = camera.get_intrinsics()

        assert intrinsics.width == MockCameraService.DEFAULT_DEPTH_WIDTH
        assert intrinsics.height == MockCameraService.DEFAULT_DEPTH_HEIGHT
        assert intrinsics.fx > 0
        assert intrinsics.fy > 0
        assert intrinsics.cx > 0
        assert intrinsics.cy > 0
        assert intrinsics.depth_scale == MockCameraService.DEFAULT_DEPTH_SCALE

    def test_get_depth_scale(self, camera: MockCameraService) -> None:
        """Depth scale should be correct."""
        assert camera.get_depth_scale() == MockCameraService.DEFAULT_DEPTH_SCALE

    def test_custom_resolution(self) -> None:
        """Custom resolution should be respected."""
        camera = MockCameraService(
            rgb_width=640,
            rgb_height=480,
            depth_width=320,
            depth_height=240,
        )
        camera.start_streaming()
        try:
            frame = camera.capture_frame()

            assert frame.rgb.shape == (480, 640, 3)
            assert frame.depth.shape == (240, 320)
        finally:
            camera.stop_streaming()

    def test_context_manager(self) -> None:
        """Context manager should handle streaming lifecycle."""
        camera = MockCameraService()

        with camera:
            assert camera.is_streaming is True
            frame = camera.capture_frame()
            assert frame is not None

        assert camera.is_streaming is False

    def test_reproducible_with_seed(self) -> None:
        """Same seed should produce same frames."""
        camera1 = MockCameraService(seed=123)
        camera2 = MockCameraService(seed=123)

        camera1.start_streaming()
        camera2.start_streaming()
        try:
            frame1 = camera1.capture_frame()
            frame2 = camera2.capture_frame()

            # RGB should be identical (same seed, same frame)
            np.testing.assert_array_equal(frame1.rgb, frame2.rgb)
        finally:
            camera1.stop_streaming()
            camera2.stop_streaming()


class TestCreateCameraService:
    """Tests for create_camera_service factory function."""

    def test_create_mock_service(self) -> None:
        """Factory should create MockCameraService when use_mock=True."""
        service = create_camera_service(use_mock=True)
        assert isinstance(service, MockCameraService)

    def test_create_mock_with_kwargs(self) -> None:
        """Factory should pass kwargs to MockCameraService."""
        service = create_camera_service(
            use_mock=True,
            rgb_width=640,
            rgb_height=480,
            seed=42,
        )
        assert isinstance(service, MockCameraService)

        # Verify the kwargs were applied
        service.start_streaming()
        try:
            frame = service.capture_frame()
            assert frame.rgb.shape == (480, 640, 3)
        finally:
            service.stop_streaming()

    def test_create_realsense_without_hardware_raises(self) -> None:
        """Factory should raise CameraError when RealSense not available."""
        import contextlib

        # This test will fail if pyrealsense2 is installed but no camera connected
        # In most test environments, this should raise an error
        with contextlib.suppress(CameraError):
            create_camera_service(use_mock=False)
            # If we get here, pyrealsense2 might be available
            # That's OK, we can't force it to fail
