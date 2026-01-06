"""Storage service for project data management."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from scan2mesh.exceptions import ConfigError, StorageError
from scan2mesh.models import CaptureMetrics, CapturePlan, FramesMetadata, ProjectConfig
from scan2mesh.utils import load_json, save_json_atomic


class StorageService:
    """Service for managing project storage.

    Handles all file I/O operations for project data including
    configuration files, frames, and metrics.

    Attributes:
        project_dir: Path to the project directory
    """

    PROJECT_CONFIG_FILE = "project.json"
    CAPTURE_PLAN_FILE = "capture_plan.json"
    FRAMES_METADATA_FILE = "frames_metadata.json"
    CAPTURE_METRICS_FILE = "capture_metrics.json"
    RAW_FRAMES_DIR = "raw_frames"

    def __init__(self, project_dir: Path) -> None:
        """Initialize StorageService.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir

    @property
    def config_path(self) -> Path:
        """Path to project configuration file."""
        return self.project_dir / self.PROJECT_CONFIG_FILE

    @property
    def capture_plan_path(self) -> Path:
        """Path to capture plan file."""
        return self.project_dir / self.CAPTURE_PLAN_FILE

    @property
    def frames_metadata_path(self) -> Path:
        """Path to frames metadata file."""
        return self.project_dir / self.FRAMES_METADATA_FILE

    @property
    def capture_metrics_path(self) -> Path:
        """Path to capture metrics file."""
        return self.project_dir / self.CAPTURE_METRICS_FILE

    @property
    def raw_frames_dir(self) -> Path:
        """Path to raw frames directory."""
        return self.project_dir / self.RAW_FRAMES_DIR

    def save_project_config(self, config: ProjectConfig) -> None:
        """Save project configuration to file.

        Args:
            config: ProjectConfig instance to save

        Raises:
            StorageError: If the save operation fails
        """
        data = config.model_dump(mode="json")
        save_json_atomic(self.config_path, data)

    def load_project_config(self) -> ProjectConfig:
        """Load project configuration from file.

        Returns:
            ProjectConfig instance

        Raises:
            ConfigError: If the configuration file is missing or invalid
        """
        if not self.config_path.exists():
            raise ConfigError(f"Project config not found: {self.config_path}")

        try:
            data = load_json(self.config_path)
            return ProjectConfig.model_validate(data)
        except StorageError:
            raise
        except Exception as e:
            raise ConfigError(f"Invalid project config: {e}") from e

    def project_exists(self) -> bool:
        """Check if a project exists at this location.

        Returns:
            True if project.json exists, False otherwise
        """
        return self.config_path.exists()

    def get_subdirectory(self, name: str) -> Path:
        """Get path to a project subdirectory.

        Args:
            name: Subdirectory name (e.g., 'raw_frames', 'asset')

        Returns:
            Path to the subdirectory
        """
        return self.project_dir / name

    def ensure_subdirectory(self, name: str) -> Path:
        """Ensure a subdirectory exists, creating it if necessary.

        Args:
            name: Subdirectory name

        Returns:
            Path to the subdirectory

        Raises:
            StorageError: If the directory cannot be created
        """
        path = self.get_subdirectory(name)
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError as e:
            raise StorageError(f"Failed to create directory {path}: {e}") from e

    def save_capture_plan(self, plan: CapturePlan) -> None:
        """Save capture plan to file.

        Args:
            plan: CapturePlan instance to save

        Raises:
            StorageError: If the save operation fails
        """
        data = plan.model_dump(mode="json")
        save_json_atomic(self.capture_plan_path, data)

    def load_capture_plan(self) -> CapturePlan:
        """Load capture plan from file.

        Returns:
            CapturePlan instance

        Raises:
            ConfigError: If the capture plan file is missing or invalid
        """
        if not self.capture_plan_path.exists():
            raise ConfigError(f"Capture plan not found: {self.capture_plan_path}")

        try:
            data = load_json(self.capture_plan_path)
            return CapturePlan.model_validate(data)
        except StorageError:
            raise
        except Exception as e:
            raise ConfigError(f"Invalid capture plan: {e}") from e

    def save_frame_data(
        self,
        frame_id: int,
        rgb: NDArray[np.uint8],
        depth: NDArray[np.uint16],
    ) -> tuple[str, str]:
        """Save RGB and depth frame data to files.

        Args:
            frame_id: Unique frame identifier
            rgb: RGB image as numpy array (H, W, 3)
            depth: Depth image as numpy array (H, W)

        Returns:
            Tuple of (rgb_path, depth_path) relative to project_dir

        Raises:
            StorageError: If the save operation fails
        """
        frames_dir = self.ensure_subdirectory(self.RAW_FRAMES_DIR)

        rgb_filename = f"frame_{frame_id:04d}_rgb.png"
        depth_filename = f"frame_{frame_id:04d}_depth.npy"

        rgb_path = frames_dir / rgb_filename
        depth_path = frames_dir / depth_filename

        try:
            # Save RGB as PNG using numpy (simple PPM-like format converted to PNG)
            # For production, we'd use PIL or cv2, but keeping dependencies minimal
            self._save_rgb_png(rgb_path, rgb)

            # Save depth as numpy array (lossless)
            np.save(depth_path, depth)

            # Return paths relative to project_dir
            rel_rgb = f"{self.RAW_FRAMES_DIR}/{rgb_filename}"
            rel_depth = f"{self.RAW_FRAMES_DIR}/{depth_filename}"

            return rel_rgb, rel_depth

        except Exception as e:
            raise StorageError(f"Failed to save frame {frame_id}: {e}") from e

    def _save_rgb_png(self, path: Path, rgb: NDArray[np.uint8]) -> None:
        """Save RGB array as PNG file.

        Uses a simple PNG encoder without external dependencies.
        For production use, consider PIL or cv2 for better compression.

        Args:
            path: Output path
            rgb: RGB image array (H, W, 3)
        """
        import struct
        import zlib

        height, width = rgb.shape[:2]

        def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
            chunk_len = struct.pack(">I", len(data))
            chunk_crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
            return chunk_len + chunk_type + data + chunk_crc

        # PNG signature
        png_data = b"\x89PNG\r\n\x1a\n"

        # IHDR chunk
        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        png_data += png_chunk(b"IHDR", ihdr_data)

        # IDAT chunk (raw image data)
        raw_data = b""
        for row in rgb:
            raw_data += b"\x00"  # Filter type: None
            raw_data += row.tobytes()

        compressed = zlib.compress(raw_data, 9)
        png_data += png_chunk(b"IDAT", compressed)

        # IEND chunk
        png_data += png_chunk(b"IEND", b"")

        path.write_bytes(png_data)

    def get_frame_path(self, frame_id: int, frame_type: str = "rgb") -> Path:
        """Get the path to a specific frame file.

        Args:
            frame_id: Frame identifier
            frame_type: Type of frame ("rgb" or "depth")

        Returns:
            Path to the frame file
        """
        if frame_type == "rgb":
            filename = f"frame_{frame_id:04d}_rgb.png"
        else:
            filename = f"frame_{frame_id:04d}_depth.npy"

        return self.raw_frames_dir / filename

    def save_frames_metadata(self, metadata: FramesMetadata) -> None:
        """Save frames metadata to file.

        Args:
            metadata: FramesMetadata instance to save

        Raises:
            StorageError: If the save operation fails
        """
        data = metadata.model_dump(mode="json")
        save_json_atomic(self.frames_metadata_path, data)

    def load_frames_metadata(self) -> FramesMetadata:
        """Load frames metadata from file.

        Returns:
            FramesMetadata instance

        Raises:
            ConfigError: If the metadata file is missing or invalid
        """
        if not self.frames_metadata_path.exists():
            raise ConfigError(
                f"Frames metadata not found: {self.frames_metadata_path}"
            )

        try:
            data = load_json(self.frames_metadata_path)
            return FramesMetadata.model_validate(data)
        except StorageError:
            raise
        except Exception as e:
            raise ConfigError(f"Invalid frames metadata: {e}") from e

    def save_capture_metrics(self, metrics: CaptureMetrics) -> None:
        """Save capture metrics to file.

        Args:
            metrics: CaptureMetrics instance to save

        Raises:
            StorageError: If the save operation fails
        """
        data = metrics.model_dump(mode="json")
        save_json_atomic(self.capture_metrics_path, data)

    def load_capture_metrics(self) -> CaptureMetrics:
        """Load capture metrics from file.

        Returns:
            CaptureMetrics instance

        Raises:
            ConfigError: If the metrics file is missing or invalid
        """
        if not self.capture_metrics_path.exists():
            raise ConfigError(
                f"Capture metrics not found: {self.capture_metrics_path}"
            )

        try:
            data = load_json(self.capture_metrics_path)
            return CaptureMetrics.model_validate(data)
        except StorageError:
            raise
        except Exception as e:
            raise ConfigError(f"Invalid capture metrics: {e}") from e
