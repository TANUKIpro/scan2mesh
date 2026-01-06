"""Storage service for project data management."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from scan2mesh.exceptions import ConfigError, StorageError
from scan2mesh.models import (
    AssetMetrics,
    CaptureMetrics,
    CapturePlan,
    FramesMetadata,
    PreprocessMetrics,
    ProjectConfig,
    ReconReport,
)
from scan2mesh.utils import load_json, save_json_atomic


# Check for Open3D availability
try:
    import open3d as o3d

    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False
    o3d = None

# Check for trimesh availability
try:
    import trimesh

    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False
    trimesh = None


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
    PREPROCESS_METRICS_FILE = "preprocess_metrics.json"
    RECON_REPORT_FILE = "recon_report.json"
    ASSET_METRICS_FILE = "asset_metrics.json"
    RAW_FRAMES_DIR = "raw_frames"
    MASKED_FRAMES_DIR = "masked_frames"
    RECON_DIR = "recon"
    ASSET_DIR = "asset"

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

    @property
    def masked_frames_dir(self) -> Path:
        """Path to masked frames directory."""
        return self.project_dir / self.MASKED_FRAMES_DIR

    @property
    def preprocess_metrics_path(self) -> Path:
        """Path to preprocess metrics file."""
        return self.project_dir / self.PREPROCESS_METRICS_FILE

    @property
    def recon_report_path(self) -> Path:
        """Path to reconstruction report file."""
        return self.project_dir / self.RECON_REPORT_FILE

    @property
    def recon_dir(self) -> Path:
        """Path to reconstruction directory."""
        return self.project_dir / self.RECON_DIR

    @property
    def asset_dir(self) -> Path:
        """Path to asset directory."""
        return self.project_dir / self.ASSET_DIR

    @property
    def asset_metrics_path(self) -> Path:
        """Path to asset metrics file."""
        return self.project_dir / self.ASSET_METRICS_FILE

    @property
    def mesh_path(self) -> Path:
        """Path to reconstructed mesh file."""
        return self.recon_dir / "mesh.ply"

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

    def load_frame_data(
        self,
        frame_id: int,
    ) -> tuple[NDArray[np.uint8], NDArray[np.uint16]]:
        """Load RGB and depth frame data from files.

        Args:
            frame_id: Frame identifier

        Returns:
            Tuple of (rgb, depth) numpy arrays

        Raises:
            StorageError: If the load operation fails
        """
        rgb_path = self.raw_frames_dir / f"frame_{frame_id:04d}_rgb.png"
        depth_path = self.raw_frames_dir / f"frame_{frame_id:04d}_depth.npy"

        try:
            # Load RGB image (simple PNG decoder)
            rgb = self._load_rgb_png(rgb_path)

            # Load depth as numpy array
            depth = np.load(depth_path)

            return rgb, depth.astype(np.uint16)

        except Exception as e:
            raise StorageError(f"Failed to load frame {frame_id}: {e}") from e

    def _load_rgb_png(self, path: Path) -> NDArray[np.uint8]:
        """Load RGB array from PNG file.

        Uses a simple PNG decoder without external dependencies.

        Args:
            path: Input path

        Returns:
            RGB image array (H, W, 3)

        Raises:
            StorageError: If the file cannot be read or decoded
        """
        import struct
        import zlib

        try:
            png_data = path.read_bytes()
        except FileNotFoundError as e:
            raise StorageError(f"PNG file not found: {path}") from e

        # Verify PNG signature
        if png_data[:8] != b"\x89PNG\r\n\x1a\n":
            raise StorageError(f"Invalid PNG signature: {path}")

        # Parse chunks
        pos = 8
        width = height = 0
        idat_data = b""

        while pos < len(png_data):
            chunk_len = struct.unpack(">I", png_data[pos : pos + 4])[0]
            chunk_type = png_data[pos + 4 : pos + 8]
            chunk_data = png_data[pos + 8 : pos + 8 + chunk_len]
            pos += 12 + chunk_len

            if chunk_type == b"IHDR":
                width, height = struct.unpack(">II", chunk_data[:8])
            elif chunk_type == b"IDAT":
                idat_data += chunk_data
            elif chunk_type == b"IEND":
                break

        # Decompress and parse image data
        raw_data = zlib.decompress(idat_data)

        # Reconstruct image (assumes filter type 0 = None for each row)
        rgb = np.zeros((height, width, 3), dtype=np.uint8)
        row_size = 1 + width * 3  # 1 byte filter + pixel data

        for y in range(height):
            row_start = y * row_size + 1  # Skip filter byte
            row_data = raw_data[row_start : row_start + width * 3]
            rgb[y] = np.frombuffer(row_data, dtype=np.uint8).reshape(width, 3)

        return rgb

    def save_masked_frame_data(
        self,
        frame_id: int,
        rgb_masked: NDArray[np.uint8],
        depth_masked: NDArray[np.uint16],
        mask: NDArray[np.uint8],
    ) -> tuple[str, str, str]:
        """Save masked RGB, depth, and mask data to files.

        Args:
            frame_id: Unique frame identifier
            rgb_masked: Masked RGB image as numpy array (H, W, 3)
            depth_masked: Masked depth image as numpy array (H, W)
            mask: Mask image as numpy array (H, W), 255=foreground, 0=background

        Returns:
            Tuple of (rgb_masked_path, depth_masked_path, mask_path) relative to project_dir

        Raises:
            StorageError: If the save operation fails
        """
        frames_dir = self.ensure_subdirectory(self.MASKED_FRAMES_DIR)

        rgb_filename = f"frame_{frame_id:04d}_rgb_masked.png"
        depth_filename = f"frame_{frame_id:04d}_depth_masked.npy"
        mask_filename = f"frame_{frame_id:04d}_mask.png"

        rgb_path = frames_dir / rgb_filename
        depth_path = frames_dir / depth_filename
        mask_path = frames_dir / mask_filename

        try:
            # Save masked RGB as PNG
            self._save_rgb_png(rgb_path, rgb_masked)

            # Save masked depth as numpy array (lossless)
            np.save(depth_path, depth_masked)

            # Save mask as grayscale PNG
            self._save_mask_png(mask_path, mask)

            # Return paths relative to project_dir
            rel_rgb = f"{self.MASKED_FRAMES_DIR}/{rgb_filename}"
            rel_depth = f"{self.MASKED_FRAMES_DIR}/{depth_filename}"
            rel_mask = f"{self.MASKED_FRAMES_DIR}/{mask_filename}"

            return rel_rgb, rel_depth, rel_mask

        except Exception as e:
            raise StorageError(f"Failed to save masked frame {frame_id}: {e}") from e

    def _save_mask_png(self, path: Path, mask: NDArray[np.uint8]) -> None:
        """Save grayscale mask array as PNG file.

        Args:
            path: Output path
            mask: Grayscale mask array (H, W)
        """
        import struct
        import zlib

        height, width = mask.shape[:2]

        def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
            chunk_len = struct.pack(">I", len(data))
            chunk_crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
            return chunk_len + chunk_type + data + chunk_crc

        # PNG signature
        png_data = b"\x89PNG\r\n\x1a\n"

        # IHDR chunk (color type 0 = grayscale)
        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
        png_data += png_chunk(b"IHDR", ihdr_data)

        # IDAT chunk (raw image data)
        raw_data = b""
        for row in mask:
            raw_data += b"\x00"  # Filter type: None
            raw_data += row.tobytes()

        compressed = zlib.compress(raw_data, 9)
        png_data += png_chunk(b"IDAT", compressed)

        # IEND chunk
        png_data += png_chunk(b"IEND", b"")

        path.write_bytes(png_data)

    def save_preprocess_metrics(self, metrics: PreprocessMetrics) -> None:
        """Save preprocess metrics to file.

        Args:
            metrics: PreprocessMetrics instance to save

        Raises:
            StorageError: If the save operation fails
        """
        data = metrics.model_dump(mode="json")
        save_json_atomic(self.preprocess_metrics_path, data)

    def load_preprocess_metrics(self) -> PreprocessMetrics:
        """Load preprocess metrics from file.

        Returns:
            PreprocessMetrics instance

        Raises:
            ConfigError: If the metrics file is missing or invalid
        """
        if not self.preprocess_metrics_path.exists():
            raise ConfigError(
                f"Preprocess metrics not found: {self.preprocess_metrics_path}"
            )

        try:
            data = load_json(self.preprocess_metrics_path)
            return PreprocessMetrics.model_validate(data)
        except StorageError:
            raise
        except Exception as e:
            raise ConfigError(f"Invalid preprocess metrics: {e}") from e

    def load_masked_frame_data(
        self,
        frame_id: int,
    ) -> tuple[NDArray[np.uint8], NDArray[np.uint16], NDArray[np.uint8]]:
        """Load masked RGB, depth, and mask data from files.

        Args:
            frame_id: Frame identifier

        Returns:
            Tuple of (rgb_masked, depth_masked, mask) numpy arrays

        Raises:
            StorageError: If the load operation fails
        """
        rgb_path = self.masked_frames_dir / f"frame_{frame_id:04d}_rgb_masked.png"
        depth_path = self.masked_frames_dir / f"frame_{frame_id:04d}_depth_masked.npy"
        mask_path = self.masked_frames_dir / f"frame_{frame_id:04d}_mask.png"

        try:
            # Load masked RGB image
            rgb = self._load_rgb_png(rgb_path)

            # Load masked depth as numpy array
            depth = np.load(depth_path).astype(np.uint16)

            # Load mask image
            mask = self._load_mask_png(mask_path)

            return rgb, depth, mask

        except Exception as e:
            raise StorageError(f"Failed to load masked frame {frame_id}: {e}") from e

    def _load_mask_png(self, path: Path) -> NDArray[np.uint8]:
        """Load grayscale mask array from PNG file.

        Args:
            path: Input path

        Returns:
            Grayscale mask array (H, W)

        Raises:
            StorageError: If the file cannot be read or decoded
        """
        import struct
        import zlib

        try:
            png_data = path.read_bytes()
        except FileNotFoundError as e:
            raise StorageError(f"Mask PNG file not found: {path}") from e

        # Verify PNG signature
        if png_data[:8] != b"\x89PNG\r\n\x1a\n":
            raise StorageError(f"Invalid PNG signature: {path}")

        # Parse chunks
        pos = 8
        width = height = 0
        idat_data = b""

        while pos < len(png_data):
            chunk_len = struct.unpack(">I", png_data[pos : pos + 4])[0]
            chunk_type = png_data[pos + 4 : pos + 8]
            chunk_data = png_data[pos + 8 : pos + 8 + chunk_len]
            pos += 12 + chunk_len

            if chunk_type == b"IHDR":
                width, height = struct.unpack(">II", chunk_data[:8])
            elif chunk_type == b"IDAT":
                idat_data += chunk_data
            elif chunk_type == b"IEND":
                break

        # Decompress and parse image data
        raw_data = zlib.decompress(idat_data)

        # Reconstruct grayscale image (assumes filter type 0 = None for each row)
        mask = np.zeros((height, width), dtype=np.uint8)
        row_size = 1 + width  # 1 byte filter + pixel data (grayscale)

        for y in range(height):
            row_start = y * row_size + 1  # Skip filter byte
            row_data = raw_data[row_start : row_start + width]
            mask[y] = np.frombuffer(row_data, dtype=np.uint8)

        return mask

    def save_mesh(self, vertices: NDArray[np.float64], triangles: NDArray[np.int64]) -> str:
        """Save mesh as PLY file.

        Args:
            vertices: Vertex array (N, 3)
            triangles: Triangle index array (M, 3)

        Returns:
            Path to saved mesh file relative to project_dir

        Raises:
            StorageError: If the save operation fails
        """
        recon_dir = self.ensure_subdirectory(self.RECON_DIR)
        mesh_path = recon_dir / "mesh.ply"

        try:
            # Write PLY file
            with mesh_path.open("w") as f:
                f.write("ply\n")
                f.write("format ascii 1.0\n")
                f.write(f"element vertex {len(vertices)}\n")
                f.write("property float x\n")
                f.write("property float y\n")
                f.write("property float z\n")
                f.write(f"element face {len(triangles)}\n")
                f.write("property list uchar int vertex_indices\n")
                f.write("end_header\n")

                # Write vertices
                for v in vertices:
                    f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

                # Write triangles
                for t in triangles:
                    f.write(f"3 {t[0]} {t[1]} {t[2]}\n")

            return f"{self.RECON_DIR}/mesh.ply"

        except Exception as e:
            raise StorageError(f"Failed to save mesh: {e}") from e

    def save_recon_report(self, report: ReconReport) -> None:
        """Save reconstruction report to file.

        Args:
            report: ReconReport instance to save

        Raises:
            StorageError: If the save operation fails
        """
        data = report.model_dump(mode="json")
        save_json_atomic(self.recon_report_path, data)

    def load_recon_report(self) -> ReconReport:
        """Load reconstruction report from file.

        Returns:
            ReconReport instance

        Raises:
            ConfigError: If the report file is missing or invalid
        """
        if not self.recon_report_path.exists():
            raise ConfigError(
                f"Reconstruction report not found: {self.recon_report_path}"
            )

        try:
            data = load_json(self.recon_report_path)
            return ReconReport.model_validate(data)
        except StorageError:
            raise
        except Exception as e:
            raise ConfigError(f"Invalid reconstruction report: {e}") from e

    def load_mesh(self) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
        """Load mesh from PLY file in recon directory.

        Returns:
            Tuple of (vertices, triangles) numpy arrays
            - vertices: (N, 3) array of vertex positions
            - triangles: (M, 3) array of triangle vertex indices

        Raises:
            StorageError: If the mesh file is missing or cannot be loaded
        """
        if not self.mesh_path.exists():
            raise StorageError(f"Mesh file not found: {self.mesh_path}")

        if HAS_OPEN3D:
            try:
                mesh = o3d.io.read_triangle_mesh(str(self.mesh_path))
                if not mesh.has_vertices():
                    raise StorageError(f"Mesh has no vertices: {self.mesh_path}")
                vertices = np.asarray(mesh.vertices).astype(np.float64)
                triangles = np.asarray(mesh.triangles).astype(np.int64)
                return vertices, triangles
            except Exception as e:
                raise StorageError(f"Failed to load mesh with Open3D: {e}") from e
        elif HAS_TRIMESH:
            try:
                mesh = trimesh.load(str(self.mesh_path))
                vertices = np.asarray(mesh.vertices).astype(np.float64)
                triangles = np.asarray(mesh.faces).astype(np.int64)
                return vertices, triangles
            except Exception as e:
                raise StorageError(f"Failed to load mesh with trimesh: {e}") from e
        else:
            # Fallback: parse PLY manually
            return self._load_mesh_ply_manual(self.mesh_path)

    def _load_mesh_ply_manual(
        self, path: Path
    ) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
        """Load PLY mesh file manually without external dependencies.

        Args:
            path: Path to PLY file

        Returns:
            Tuple of (vertices, triangles) numpy arrays

        Raises:
            StorageError: If parsing fails
        """
        try:
            with path.open("r") as f:
                lines = f.readlines()

            # Parse header
            num_vertices = 0
            num_faces = 0
            header_end = 0

            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith("element vertex"):
                    num_vertices = int(line.split()[-1])
                elif line.startswith("element face"):
                    num_faces = int(line.split()[-1])
                elif line == "end_header":
                    header_end = i + 1
                    break

            if num_vertices == 0:
                raise StorageError("PLY file has no vertices")

            # Parse vertices
            vertices = np.zeros((num_vertices, 3), dtype=np.float64)
            for i in range(num_vertices):
                parts = lines[header_end + i].strip().split()
                vertices[i] = [float(parts[0]), float(parts[1]), float(parts[2])]

            # Parse faces
            triangles = np.zeros((num_faces, 3), dtype=np.int64)
            for i in range(num_faces):
                parts = lines[header_end + num_vertices + i].strip().split()
                # First number is face vertex count, followed by indices
                triangles[i] = [int(parts[1]), int(parts[2]), int(parts[3])]

            return vertices, triangles

        except Exception as e:
            raise StorageError(f"Failed to parse PLY file: {e}") from e

    def save_asset_mesh(
        self,
        vertices: NDArray[np.float64],
        triangles: NDArray[np.int64],
        filename: str,
        file_format: str = "glb",
    ) -> str:
        """Save mesh to asset directory in specified format.

        Args:
            vertices: Vertex array (N, 3)
            triangles: Triangle index array (M, 3)
            filename: Output filename (without extension)
            file_format: Output format ("glb", "obj", "ply")

        Returns:
            Path to saved mesh file relative to project_dir

        Raises:
            StorageError: If the save operation fails
        """
        asset_dir = self.ensure_subdirectory(self.ASSET_DIR)

        if file_format == "glb":
            output_path = asset_dir / f"{filename}.glb"
            self._save_mesh_glb(output_path, vertices, triangles)
        elif file_format == "obj":
            output_path = asset_dir / f"{filename}.obj"
            self._save_mesh_obj(output_path, vertices, triangles)
        elif file_format == "ply":
            output_path = asset_dir / f"{filename}.ply"
            self._save_mesh_ply(output_path, vertices, triangles)
        else:
            raise StorageError(f"Unsupported mesh format: {file_format}")

        return f"{self.ASSET_DIR}/{output_path.name}"

    def _save_mesh_glb(
        self,
        path: Path,
        vertices: NDArray[np.float64],
        triangles: NDArray[np.int64],
    ) -> None:
        """Save mesh as GLB file.

        Args:
            path: Output path
            vertices: Vertex array (N, 3)
            triangles: Triangle index array (M, 3)

        Raises:
            StorageError: If trimesh is not available or save fails
        """
        if not HAS_TRIMESH:
            raise StorageError(
                "trimesh is required for GLB export. Install with: uv add trimesh"
            )

        try:
            mesh = trimesh.Trimesh(vertices=vertices, faces=triangles)
            mesh.export(str(path), file_type="glb")
        except Exception as e:
            raise StorageError(f"Failed to save GLB mesh: {e}") from e

    def _save_mesh_obj(
        self,
        path: Path,
        vertices: NDArray[np.float64],
        triangles: NDArray[np.int64],
    ) -> None:
        """Save mesh as OBJ file.

        Args:
            path: Output path
            vertices: Vertex array (N, 3)
            triangles: Triangle index array (M, 3)
        """
        try:
            with path.open("w") as f:
                f.write("# OBJ file generated by scan2mesh\n")

                # Write vertices
                for v in vertices:
                    f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

                # Write faces (OBJ uses 1-based indices)
                for t in triangles:
                    f.write(f"f {t[0] + 1} {t[1] + 1} {t[2] + 1}\n")

        except Exception as e:
            raise StorageError(f"Failed to save OBJ mesh: {e}") from e

    def _save_mesh_ply(
        self,
        path: Path,
        vertices: NDArray[np.float64],
        triangles: NDArray[np.int64],
    ) -> None:
        """Save mesh as PLY file.

        Args:
            path: Output path
            vertices: Vertex array (N, 3)
            triangles: Triangle index array (M, 3)
        """
        try:
            with path.open("w") as f:
                f.write("ply\n")
                f.write("format ascii 1.0\n")
                f.write(f"element vertex {len(vertices)}\n")
                f.write("property float x\n")
                f.write("property float y\n")
                f.write("property float z\n")
                f.write(f"element face {len(triangles)}\n")
                f.write("property list uchar int vertex_indices\n")
                f.write("end_header\n")

                for v in vertices:
                    f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

                for t in triangles:
                    f.write(f"3 {t[0]} {t[1]} {t[2]}\n")

        except Exception as e:
            raise StorageError(f"Failed to save PLY mesh: {e}") from e

    def save_preview_image(
        self,
        image: NDArray[np.uint8],
        filename: str = "preview.png",
    ) -> str:
        """Save preview image to asset directory.

        Args:
            image: RGB image array (H, W, 3)
            filename: Output filename

        Returns:
            Path to saved image file relative to project_dir

        Raises:
            StorageError: If the save operation fails
        """
        asset_dir = self.ensure_subdirectory(self.ASSET_DIR)
        output_path = asset_dir / filename

        try:
            self._save_rgb_png(output_path, image)
            return f"{self.ASSET_DIR}/{filename}"
        except Exception as e:
            raise StorageError(f"Failed to save preview image: {e}") from e

    def save_asset_metrics(self, metrics: AssetMetrics) -> None:
        """Save asset metrics to file.

        Args:
            metrics: AssetMetrics instance to save

        Raises:
            StorageError: If the save operation fails
        """
        data = metrics.model_dump(mode="json")
        save_json_atomic(self.asset_metrics_path, data)

    def load_asset_metrics(self) -> AssetMetrics:
        """Load asset metrics from file.

        Returns:
            AssetMetrics instance

        Raises:
            ConfigError: If the metrics file is missing or invalid
        """
        if not self.asset_metrics_path.exists():
            raise ConfigError(f"Asset metrics not found: {self.asset_metrics_path}")

        try:
            data = load_json(self.asset_metrics_path)
            return AssetMetrics.model_validate(data)
        except StorageError:
            raise
        except Exception as e:
            raise ConfigError(f"Invalid asset metrics: {e}") from e
