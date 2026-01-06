"""RealSense device management service."""


import numpy as np

from scan2mesh_gui.models.device import DeviceInfo


class DeviceService:
    """Service for managing RealSense devices."""

    def __init__(self) -> None:
        self._mock_mode = True  # Use mock mode when pyrealsense2 is not available

    def list_devices(self) -> list[DeviceInfo]:
        """List all connected RealSense devices."""
        if self._mock_mode:
            return self._get_mock_devices()

        # TODO: Implement real device detection with pyrealsense2
        return []

    def get_device(self, serial_number: str) -> DeviceInfo | None:
        """Get a device by serial number."""
        devices = self.list_devices()
        for device in devices:
            if device.serial_number == serial_number:
                return device
        return None

    def test_capture(
        self, serial_number: str
    ) -> tuple[np.ndarray, np.ndarray] | None:
        """Capture a test frame (RGB, Depth)."""
        if self._mock_mode:
            return self._get_mock_frames()

        # TODO: Implement real capture with pyrealsense2
        return None

    def set_resolution(
        self,
        serial_number: str,
        color_resolution: tuple[int, int],
        depth_resolution: tuple[int, int],
        fps: int,
    ) -> bool:
        """Set device resolution settings."""
        if self._mock_mode:
            return True

        # TODO: Implement real resolution setting
        return False

    def is_connected(self, serial_number: str) -> bool:
        """Check if a device is connected."""
        device = self.get_device(serial_number)
        return device is not None and device.is_connected

    def _get_mock_devices(self) -> list[DeviceInfo]:
        """Return mock devices for development."""
        return [
            DeviceInfo(
                serial_number="MOCK001",
                name="Intel RealSense D435 (Mock)",
                firmware_version="5.15.0.0",
                usb_type="3.2",
                is_connected=True,
                color_resolutions=[(1920, 1080), (1280, 720), (640, 480)],
                depth_resolutions=[(1280, 720), (848, 480), (640, 480)],
                current_color_resolution=(1920, 1080),
                current_depth_resolution=(1280, 720),
                current_fps=30,
            )
        ]

    def _get_mock_frames(self) -> tuple[np.ndarray, np.ndarray]:
        """Return mock frames for development."""
        # Generate a simple test pattern
        rgb = np.zeros((720, 1280, 3), dtype=np.uint8)
        # Gradient pattern
        for i in range(720):
            for j in range(1280):
                rgb[i, j] = [j % 256, i % 256, (i + j) % 256]

        depth = np.zeros((720, 1280), dtype=np.uint16)
        # Simple depth gradient
        for i in range(720):
            for j in range(1280):
                depth[i, j] = int(500 + (j / 1280) * 2000)

        return rgb, depth
