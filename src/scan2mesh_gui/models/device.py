"""DeviceInfo model for RealSense camera information."""


from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """Information about a connected RealSense device."""

    serial_number: str
    name: str = Field(..., description="Device name (e.g., 'Intel RealSense D435')")
    firmware_version: str
    usb_type: str = Field(..., description="USB specification (e.g., '3.2')")
    is_connected: bool = True

    # Supported resolutions
    color_resolutions: list[tuple[int, int]] = Field(default_factory=list)
    depth_resolutions: list[tuple[int, int]] = Field(default_factory=list)

    # Current settings
    current_color_resolution: tuple[int, int] | None = None
    current_depth_resolution: tuple[int, int] | None = None
    current_fps: int = 30

    model_config = {
        "json_schema_extra": {
            "example": {
                "serial_number": "123456789",
                "name": "Intel RealSense D435",
                "firmware_version": "5.15.0.0",
                "usb_type": "3.2",
                "is_connected": True,
                "color_resolutions": [(1920, 1080), (1280, 720), (640, 480)],
                "depth_resolutions": [(1280, 720), (848, 480), (640, 480)],
                "current_color_resolution": (1920, 1080),
                "current_depth_resolution": (1280, 720),
                "current_fps": 30,
            }
        }
    }
