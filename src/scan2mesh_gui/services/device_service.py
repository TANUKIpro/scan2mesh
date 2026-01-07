"""RealSense device management service."""

from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from scan2mesh_gui.models.device import DeviceInfo

# Try to import pyrealsense2
try:
    import pyrealsense2 as rs

    _HAS_REALSENSE = True
except ImportError:
    _HAS_REALSENSE = False
    rs = None  # type: ignore[assignment]

if TYPE_CHECKING:
    import pyrealsense2 as rs  # noqa: F811


# Module-level state to persist across Streamlit reruns
_device_settings: dict[str, dict[str, tuple[int, int] | int]] = {}
_selected_serial: str | None = None


class DeviceService:
    """Service for managing RealSense devices."""

    def __init__(self, force_mock: bool = False) -> None:
        """Initialize device service.

        Args:
            force_mock: Force mock mode even if pyrealsense2 is available
        """
        self._mock_mode = force_mock or not _HAS_REALSENSE
        self._context: Any = None

        if not self._mock_mode and rs is not None:
            try:
                self._context = rs.context()
            except Exception:
                # RealSense initialization failed, fall back to mock mode
                self._mock_mode = True

    @property
    def is_mock_mode(self) -> bool:
        """Check if service is running in mock mode."""
        return self._mock_mode

    def list_devices(self) -> list[DeviceInfo]:
        """List all connected RealSense devices."""
        if self._mock_mode:
            return self._get_mock_devices()

        if self._context is None or rs is None:
            return []

        devices: list[DeviceInfo] = []

        try:
            for device in self._context.query_devices():
                serial = device.get_info(rs.camera_info.serial_number)
                name = device.get_info(rs.camera_info.name)
                firmware = device.get_info(rs.camera_info.firmware_version)

                # Get USB type (may not be available on all devices)
                try:
                    usb_type = device.get_info(rs.camera_info.usb_type_descriptor)
                except Exception:
                    usb_type = "Unknown"

                # Get supported resolutions
                color_resolutions = self._get_supported_resolutions(
                    device, rs.stream.color
                )
                depth_resolutions = self._get_supported_resolutions(
                    device, rs.stream.depth
                )

                # Use default resolutions if none found
                if not color_resolutions:
                    color_resolutions = [(1920, 1080), (1280, 720), (640, 480)]
                if not depth_resolutions:
                    depth_resolutions = [(1280, 720), (848, 480), (640, 480)]

                # Get current settings if available
                settings = _device_settings.get(serial, {})
                current_color = settings.get("color_resolution")
                current_depth = settings.get("depth_resolution")
                current_fps = settings.get("fps", 30)

                devices.append(
                    DeviceInfo(
                        serial_number=serial,
                        name=name,
                        firmware_version=firmware,
                        usb_type=usb_type,
                        is_connected=True,
                        color_resolutions=color_resolutions,
                        depth_resolutions=depth_resolutions,
                        current_color_resolution=(
                            current_color
                            if isinstance(current_color, tuple)
                            else color_resolutions[0] if color_resolutions else (1920, 1080)
                        ),
                        current_depth_resolution=(
                            current_depth
                            if isinstance(current_depth, tuple)
                            else depth_resolutions[0] if depth_resolutions else (1280, 720)
                        ),
                        current_fps=current_fps if isinstance(current_fps, int) else 30,
                    )
                )
        except Exception:
            # Device enumeration failed, return mock devices
            return self._get_mock_devices()

        # If no real devices found, return mock device for development
        if not devices:
            return self._get_mock_devices()

        return devices

    def _get_supported_resolutions(
        self,
        device: Any,
        stream_type: Any,
    ) -> list[tuple[int, int]]:
        """Get supported resolutions for a stream type."""
        if rs is None:
            return []

        resolutions: set[tuple[int, int]] = set()

        try:
            for sensor in device.query_sensors():
                for profile in sensor.get_stream_profiles():
                    if profile.stream_type() == stream_type:
                        video_profile = profile.as_video_stream_profile()
                        resolutions.add(
                            (video_profile.width(), video_profile.height())
                        )
        except Exception:
            pass

        # Sort by resolution (descending)
        return sorted(list(resolutions), key=lambda x: x[0] * x[1], reverse=True)

    def get_device(self, serial_number: str) -> DeviceInfo | None:
        """Get a device by serial number."""
        devices = self.list_devices()
        for device in devices:
            if device.serial_number == serial_number:
                return device
        return None

    def test_capture(
        self, serial_number: str
    ) -> tuple[npt.NDArray[np.uint8], npt.NDArray[np.uint16]] | None:
        """Capture a test frame (RGB, Depth).

        Args:
            serial_number: Device serial number

        Returns:
            Tuple of (RGB, Depth) frames or None if capture failed
        """
        if self._mock_mode:
            return self._get_mock_frames()

        if rs is None:
            return self._get_mock_frames()

        # Check if this is a mock device
        if serial_number.startswith("MOCK"):
            return self._get_mock_frames()

        try:
            # Create pipeline for this capture
            pipeline = rs.pipeline()
            config = rs.config()

            # Enable specific device
            config.enable_device(serial_number)

            # Get current resolution settings
            settings = _device_settings.get(serial_number, {})
            color_res = settings.get("color_resolution", (1920, 1080))
            depth_res = settings.get("depth_resolution", (1280, 720))
            fps = settings.get("fps", 30)

            if (
                isinstance(color_res, tuple)
                and isinstance(depth_res, tuple)
                and isinstance(fps, int)
            ):
                config.enable_stream(
                    rs.stream.color, color_res[0], color_res[1], rs.format.bgr8, fps
                )
                config.enable_stream(
                    rs.stream.depth, depth_res[0], depth_res[1], rs.format.z16, fps
                )

            # Start pipeline
            pipeline.start(config)

            try:
                # Wait for frames (with timeout)
                frames = pipeline.wait_for_frames(timeout_ms=5000)

                # Get color and depth frames
                color_frame = frames.get_color_frame()
                depth_frame = frames.get_depth_frame()

                if not color_frame or not depth_frame:
                    return None

                # Convert to numpy arrays
                rgb = np.asanyarray(color_frame.get_data())
                # BGR to RGB
                rgb = rgb[:, :, ::-1].copy().astype(np.uint8)

                depth = np.asanyarray(depth_frame.get_data()).astype(np.uint16)

                return rgb, depth

            finally:
                pipeline.stop()

        except Exception as e:
            # Log error for debugging
            print(f"RealSense capture error: {e}")
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

        # Store settings in module-level dict (used by both mock and real mode)
        _device_settings[serial_number] = {
            "color_resolution": color_resolution,
            "depth_resolution": depth_resolution,
            "fps": fps,
        }

        # In real mode, validate that the resolution is supported
        if not self._mock_mode and not serial_number.startswith("MOCK"):
            device = self.get_device(serial_number)
            if device is None:
                return False

            # Check if color resolution is supported
            if color_resolution not in device.color_resolutions:
                return False

            # Check if depth resolution is supported
            if depth_resolution not in device.depth_resolutions:
                return False

        return True

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

    def _get_mock_frames(
        self,
    ) -> tuple[npt.NDArray[np.uint8], npt.NDArray[np.uint16]]:
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
