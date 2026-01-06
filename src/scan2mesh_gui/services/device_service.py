"""RealSense device management service."""

import numpy as np
import numpy.typing as npt

from scan2mesh_gui.models.device import DeviceInfo


# Module-level state to persist across Streamlit reruns
_device_settings: dict[str, dict[str, tuple[int, int] | int]] = {}
_selected_serial: str | None = None


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
        self, serial_number: str  # noqa: ARG002
    ) -> tuple[npt.NDArray[np.uint8], npt.NDArray[np.uint16]] | None:
        """Capture a test frame (RGB, Depth).

        Args:
            serial_number: Device serial number (used in real mode)

        Returns:
            Tuple of (RGB, Depth) frames or None if capture failed
        """
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
        global _device_settings

        if self._mock_mode:
            # Store settings in module-level dict
            _device_settings[serial_number] = {
                "color_resolution": color_resolution,
                "depth_resolution": depth_resolution,
                "fps": fps,
            }
            return True

        # TODO: Implement real resolution setting
        return False

    def select_device(self, serial_number: str) -> bool:
        """Select a device for use in capture and other operations.

        Args:
            serial_number: Serial number of device to select

        Returns:
            True if device was found and selected, False otherwise
        """
        global _selected_serial

        device = self.get_device(serial_number)
        if device is not None:
            _selected_serial = serial_number
            return True
        return False

    def get_selected_device(self) -> DeviceInfo | None:
        """Get the currently selected device.

        Returns:
            DeviceInfo if a device is selected, None otherwise
        """
        global _selected_serial

        if _selected_serial is None:
            return None
        return self.get_device(_selected_serial)

    def get_selected_serial(self) -> str | None:
        """Get the serial number of the currently selected device.

        Returns:
            Serial number if a device is selected, None otherwise
        """
        global _selected_serial
        return _selected_serial

    def clear_selection(self) -> None:
        """Clear the current device selection."""
        global _selected_serial
        _selected_serial = None

    def is_connected(self, serial_number: str) -> bool:
        """Check if a device is connected."""
        device = self.get_device(serial_number)
        return device is not None and device.is_connected

    def _get_mock_devices(self) -> list[DeviceInfo]:
        """Return mock devices for development."""
        global _device_settings

        # Default mock device configuration
        mock_serial = "MOCK001"
        default_color = (1920, 1080)
        default_depth = (1280, 720)
        default_fps = 30

        # Apply saved settings if available
        if mock_serial in _device_settings:
            settings = _device_settings[mock_serial]
            color_res = settings.get("color_resolution", default_color)
            depth_res = settings.get("depth_resolution", default_depth)
            fps = settings.get("fps", default_fps)
            # Ensure proper types
            if isinstance(color_res, tuple):
                default_color = color_res
            if isinstance(depth_res, tuple):
                default_depth = depth_res
            if isinstance(fps, int):
                default_fps = fps

        return [
            DeviceInfo(
                serial_number=mock_serial,
                name="Intel RealSense D435 (Mock)",
                firmware_version="5.15.0.0",
                usb_type="3.2",
                is_connected=True,
                color_resolutions=[(1920, 1080), (1280, 720), (640, 480)],
                depth_resolutions=[(1280, 720), (848, 480), (640, 480)],
                current_color_resolution=default_color,
                current_depth_resolution=default_depth,
                current_fps=default_fps,
            )
        ]

    def _get_mock_frames(self) -> tuple[npt.NDArray[np.uint8], npt.NDArray[np.uint16]]:
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
