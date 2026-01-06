"""Asset optimization stage.

This module provides the AssetOptimizer class for optimizing 3D assets
generated from reconstruction.
"""

import logging
import time
from pathlib import Path
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from scan2mesh.exceptions import PipelineError, StorageError
from scan2mesh.models import (
    AssetMetrics,
    CollisionMetrics,
    LODMetrics,
    OutputPreset,
    ProjectConfig,
    ScaleInfo,
)
from scan2mesh.services import StorageService


logger = logging.getLogger("scan2mesh.stages.optimize")

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


class AssetOptimizer:
    """Optimize reconstructed mesh for target use cases.

    This stage handles:
    - Coordinate axis normalization (Z-up, origin at bottom center)
    - Scale application from known dimensions or RealSense depth
    - Mesh repair (normals, non-manifold edges, holes)
    - LOD generation (100k, 30k, 10k triangles)
    - Collision mesh generation (convex hull)
    - Preview image generation

    Attributes:
        project_dir: Path to the project directory
        storage: Storage service instance
        output_preset: Output configuration preset
        scale_info: Scale information for the object
    """

    # LOD triangle limits
    LOD_LIMITS: ClassVar[list[int]] = [100_000, 30_000, 10_000]

    # Texture defaults (placeholder until texture generation is implemented)
    DEFAULT_TEXTURE_RESOLUTION = 2048
    DEFAULT_TEXTURE_COVERAGE = 0.0  # No texture generated yet

    def __init__(
        self,
        project_dir: Path,
        storage: StorageService | None = None,
    ) -> None:
        """Initialize AssetOptimizer.

        Args:
            project_dir: Path to the project directory
            storage: Storage service instance (optional)
        """
        self.project_dir = project_dir
        self.storage = storage or StorageService(project_dir)

        # Load project configuration
        self._config: ProjectConfig | None = None
        self._output_preset: OutputPreset | None = None
        self._scale_info: ScaleInfo | None = None

        # State
        self._vertices: NDArray[np.float64] | None = None
        self._triangles: NDArray[np.int64] | None = None

    def _load_config(self) -> None:
        """Load project configuration.

        Raises:
            PipelineError: If project configuration cannot be loaded
        """
        try:
            self._config = self.storage.load_project_config()
            self._output_preset = self._config.output_preset
            self._scale_info = self._config.scale_info
        except Exception as e:
            raise PipelineError(f"Failed to load project configuration: {e}") from e

    @property
    def output_preset(self) -> OutputPreset:
        """Get output preset configuration."""
        if self._output_preset is None:
            self._load_config()
        assert self._output_preset is not None
        return self._output_preset

    @property
    def scale_info(self) -> ScaleInfo | None:
        """Get scale information."""
        if self._config is None:
            self._load_config()
        return self._scale_info

    def _load_mesh(self) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
        """Load mesh from reconstruction directory.

        Returns:
            Tuple of (vertices, triangles) numpy arrays

        Raises:
            PipelineError: If mesh cannot be loaded
        """
        try:
            vertices, triangles = self.storage.load_mesh()
            self._vertices = vertices
            self._triangles = triangles
            logger.info(
                f"Loaded mesh: {len(vertices)} vertices, {len(triangles)} triangles"
            )
            return vertices, triangles
        except StorageError as e:
            raise PipelineError(f"Failed to load mesh: {e}") from e

    def normalize_axes(
        self,
        vertices: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Normalize mesh axes to Z-up with origin at bottom center.

        The coordinate system is normalized to:
        - Z axis pointing up
        - Origin at the center of the bottom face (XY plane at minimum Z)

        Args:
            vertices: Vertex array (N, 3)

        Returns:
            Normalized vertex array (N, 3)
        """
        if len(vertices) == 0:
            return vertices

        # Get current axis configuration from output preset
        coord_sys = self.output_preset.coordinate_system

        # Current implementation assumes mesh is already in a reasonable orientation
        # Only apply origin transformation to bottom center

        # Find bounding box
        min_coords = np.min(vertices, axis=0)
        max_coords = np.max(vertices, axis=0)

        # Calculate center of XY plane and bottom Z
        center_x = (min_coords[0] + max_coords[0]) / 2
        center_y = (min_coords[1] + max_coords[1]) / 2
        bottom_z = min_coords[2]

        # Translate to place origin at bottom center
        if coord_sys.origin == "bottom_center":
            translation = np.array([center_x, center_y, bottom_z])
            normalized = vertices - translation
        elif coord_sys.origin == "centroid":
            centroid = np.mean(vertices, axis=0)
            normalized = vertices - centroid
        else:
            # Default: bottom center
            translation = np.array([center_x, center_y, bottom_z])
            normalized = vertices - translation

        logger.debug(
            f"Normalized axes: origin={coord_sys.origin}, "
            f"translation={translation if coord_sys.origin == 'bottom_center' else 'centroid'}"
        )

        result: NDArray[np.float64] = normalized.astype(np.float64)
        return result

    def apply_scale(
        self,
        vertices: NDArray[np.float64],
    ) -> tuple[NDArray[np.float64], str]:
        """Apply scale based on scale information.

        Args:
            vertices: Vertex array (N, 3)

        Returns:
            Tuple of (scaled vertices, scale uncertainty level)
        """
        if len(vertices) == 0:
            return vertices, "high"

        scale_info = self.scale_info

        if scale_info is None:
            # No scale info: use RealSense scale (assume already in meters)
            logger.info("No scale info provided, using raw RealSense scale")
            return vertices, "high"

        if scale_info.method == "known_dimension" and scale_info.known_dimension_mm:
            # Calculate current dimension
            min_coords = np.min(vertices, axis=0)
            max_coords = np.max(vertices, axis=0)
            dimensions = max_coords - min_coords

            # Determine which dimension to use for scaling
            dim_type = scale_info.dimension_type or "diameter"
            if dim_type == "diameter":
                # Use maximum of X and Y as diameter
                current_dim = max(dimensions[0], dimensions[1])
            elif dim_type == "width":
                current_dim = dimensions[0]
            elif dim_type == "height":
                current_dim = dimensions[2]  # Z is up
            elif dim_type == "length" or dim_type == "depth":
                current_dim = dimensions[1]
            else:
                current_dim = max(dimensions[0], dimensions[1])

            # Calculate scale factor
            target_dim_m = scale_info.known_dimension_mm / 1000.0  # mm to meters
            if current_dim > 0:
                scale_factor = target_dim_m / current_dim
                scaled = vertices * scale_factor
                logger.info(
                    f"Applied known dimension scale: {scale_info.known_dimension_mm}mm "
                    f"({dim_type}), scale factor={scale_factor:.4f}"
                )
                return scaled.astype(np.float64), "low"
            else:
                logger.warning("Current dimension is zero, cannot apply scale")
                return vertices, "high"

        elif scale_info.method == "realsense_depth_scale":
            # RealSense depth is already in meters
            logger.info("Using RealSense depth scale (already in meters)")
            return vertices, "medium"

        return vertices, scale_info.uncertainty

    def repair_mesh(
        self,
        vertices: NDArray[np.float64],
        triangles: NDArray[np.int64],
    ) -> tuple[NDArray[np.float64], NDArray[np.int64], int]:
        """Repair mesh by fixing common issues.

        Repairs:
        - Consistent normal orientation
        - Non-manifold edge removal
        - Isolated vertex removal

        Args:
            vertices: Vertex array (N, 3)
            triangles: Triangle index array (M, 3)

        Returns:
            Tuple of (repaired vertices, repaired triangles, non_manifold_edges count)
        """
        non_manifold_count = 0

        if HAS_OPEN3D:
            try:
                mesh = o3d.geometry.TriangleMesh()
                mesh.vertices = o3d.utility.Vector3dVector(vertices)
                mesh.triangles = o3d.utility.Vector3iVector(triangles)

                # Compute normals
                mesh.compute_vertex_normals()

                # Remove degenerate triangles
                mesh = mesh.remove_degenerate_triangles()
                mesh = mesh.remove_duplicated_triangles()
                mesh = mesh.remove_duplicated_vertices()

                # Try to remove non-manifold edges
                non_manifold_edges = mesh.get_non_manifold_edges()
                non_manifold_count = len(non_manifold_edges)
                if non_manifold_count > 0:
                    mesh = mesh.remove_non_manifold_edges()
                    logger.info(f"Removed {non_manifold_count} non-manifold edges")

                # Remove unreferenced vertices
                mesh = mesh.remove_unreferenced_vertices()

                repaired_vertices = np.asarray(mesh.vertices).astype(np.float64)
                repaired_triangles = np.asarray(mesh.triangles).astype(np.int64)

                logger.info(
                    f"Mesh repair complete: {len(repaired_vertices)} vertices, "
                    f"{len(repaired_triangles)} triangles"
                )
                return repaired_vertices, repaired_triangles, non_manifold_count

            except Exception as e:
                logger.warning(f"Open3D mesh repair failed: {e}")
                return vertices, triangles, 0

        elif HAS_TRIMESH:
            try:
                mesh = trimesh.Trimesh(vertices=vertices, faces=triangles)
                # Trimesh automatically cleans up some issues
                mesh.fix_normals()
                mesh.remove_degenerate_faces()
                mesh.remove_duplicate_faces()
                mesh.remove_unreferenced_vertices()

                repaired_vertices = np.asarray(mesh.vertices).astype(np.float64)
                repaired_triangles = np.asarray(mesh.faces).astype(np.int64)

                logger.info(
                    f"Mesh repair complete (trimesh): {len(repaired_vertices)} vertices, "
                    f"{len(repaired_triangles)} triangles"
                )
                return repaired_vertices, repaired_triangles, 0

            except Exception as e:
                logger.warning(f"trimesh mesh repair failed: {e}")
                return vertices, triangles, 0

        else:
            logger.warning("No mesh library available for repair, skipping")
            return vertices, triangles, 0

    def generate_lod(
        self,
        vertices: NDArray[np.float64],
        triangles: NDArray[np.int64],
        target_triangles: int,
    ) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
        """Generate Level of Detail mesh by simplification.

        Args:
            vertices: Vertex array (N, 3)
            triangles: Triangle index array (M, 3)
            target_triangles: Target number of triangles

        Returns:
            Tuple of (simplified vertices, simplified triangles)
        """
        current_triangles = len(triangles)

        if current_triangles <= target_triangles:
            logger.debug(
                f"Mesh already has {current_triangles} triangles, "
                f"no simplification needed for target {target_triangles}"
            )
            return vertices, triangles

        if HAS_OPEN3D:
            try:
                mesh = o3d.geometry.TriangleMesh()
                mesh.vertices = o3d.utility.Vector3dVector(vertices)
                mesh.triangles = o3d.utility.Vector3iVector(triangles)

                # Use quadric decimation
                simplified = mesh.simplify_quadric_decimation(target_triangles)

                simp_vertices = np.asarray(simplified.vertices).astype(np.float64)
                simp_triangles = np.asarray(simplified.triangles).astype(np.int64)

                logger.info(
                    f"Simplified mesh from {current_triangles} to "
                    f"{len(simp_triangles)} triangles (target: {target_triangles})"
                )
                return simp_vertices, simp_triangles

            except Exception as e:
                logger.warning(f"Open3D simplification failed: {e}")
                return vertices, triangles

        elif HAS_TRIMESH:
            try:
                mesh = trimesh.Trimesh(vertices=vertices, faces=triangles)
                # Calculate ratio for simplification
                ratio = target_triangles / current_triangles
                simplified = mesh.simplify_quadric_decimation(
                    int(current_triangles * ratio)
                )

                simp_vertices = np.asarray(simplified.vertices).astype(np.float64)
                simp_triangles = np.asarray(simplified.faces).astype(np.int64)

                logger.info(
                    f"Simplified mesh (trimesh) from {current_triangles} to "
                    f"{len(simp_triangles)} triangles"
                )
                return simp_vertices, simp_triangles

            except Exception as e:
                logger.warning(f"trimesh simplification failed: {e}")
                return vertices, triangles

        else:
            logger.warning("No mesh library available for LOD generation")
            return vertices, triangles

    def generate_collision(
        self,
        vertices: NDArray[np.float64],
    ) -> tuple[NDArray[np.float64], NDArray[np.int64], int]:
        """Generate collision mesh using convex hull.

        Args:
            vertices: Vertex array (N, 3)

        Returns:
            Tuple of (hull vertices, hull triangles, num_convex_parts)
        """
        if HAS_TRIMESH:
            try:
                # Create convex hull using trimesh
                point_cloud = trimesh.PointCloud(vertices)
                hull = point_cloud.convex_hull

                hull_vertices = np.asarray(hull.vertices).astype(np.float64)
                hull_triangles = np.asarray(hull.faces).astype(np.int64)

                logger.info(
                    f"Generated convex hull: {len(hull_vertices)} vertices, "
                    f"{len(hull_triangles)} triangles"
                )
                return hull_vertices, hull_triangles, 1

            except Exception as e:
                logger.warning(f"Convex hull generation failed: {e}")
                # Return original mesh as fallback
                return vertices, np.zeros((0, 3), dtype=np.int64), 0

        elif HAS_OPEN3D:
            try:
                pcd = o3d.geometry.PointCloud()
                pcd.points = o3d.utility.Vector3dVector(vertices)
                hull, _ = pcd.compute_convex_hull()

                hull_vertices = np.asarray(hull.vertices).astype(np.float64)
                hull_triangles = np.asarray(hull.triangles).astype(np.int64)

                logger.info(
                    f"Generated convex hull (Open3D): {len(hull_vertices)} vertices, "
                    f"{len(hull_triangles)} triangles"
                )
                return hull_vertices, hull_triangles, 1

            except Exception as e:
                logger.warning(f"Open3D convex hull generation failed: {e}")
                return vertices, np.zeros((0, 3), dtype=np.int64), 0

        else:
            logger.warning("No mesh library available for collision mesh generation")
            return vertices, np.zeros((0, 3), dtype=np.int64), 0

    def generate_preview(
        self,
        vertices: NDArray[np.float64],
        triangles: NDArray[np.int64],
        width: int = 512,
        height: int = 512,
    ) -> NDArray[np.uint8]:
        """Generate preview image of the mesh.

        Args:
            vertices: Vertex array (N, 3)
            triangles: Triangle index array (M, 3)
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            RGB image array (H, W, 3)
        """
        if HAS_OPEN3D:
            try:
                mesh = o3d.geometry.TriangleMesh()
                mesh.vertices = o3d.utility.Vector3dVector(vertices)
                mesh.triangles = o3d.utility.Vector3iVector(triangles)
                mesh.compute_vertex_normals()

                # Paint mesh with a default color
                mesh.paint_uniform_color([0.7, 0.7, 0.7])

                # Create offscreen renderer
                vis = o3d.visualization.Visualizer()
                vis.create_window(visible=False, width=width, height=height)
                vis.add_geometry(mesh)

                # Set camera view
                ctr = vis.get_view_control()
                ctr.set_zoom(0.8)

                # Render
                vis.poll_events()
                vis.update_renderer()

                # Capture image
                image = vis.capture_screen_float_buffer(do_render=True)
                vis.destroy_window()

                # Convert to uint8
                image_array = (np.asarray(image) * 255).astype(np.uint8)
                logger.info(f"Generated preview image: {width}x{height}")
                return image_array

            except Exception as e:
                logger.warning(f"Open3D preview generation failed: {e}")
                # Return placeholder image
                return self._create_placeholder_image(width, height)
        else:
            logger.warning("No mesh library available for preview generation")
            return self._create_placeholder_image(width, height)

    def _create_placeholder_image(
        self, width: int, height: int
    ) -> NDArray[np.uint8]:
        """Create a placeholder preview image.

        Args:
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            Gray placeholder image (H, W, 3)
        """
        # Create gray background
        image = np.full((height, width, 3), 200, dtype=np.uint8)
        return image

    def _calculate_bounding_box(
        self,
        vertices: NDArray[np.float64],
    ) -> tuple[list[float], list[float]]:
        """Calculate axis-aligned and oriented bounding box sizes.

        Args:
            vertices: Vertex array (N, 3)

        Returns:
            Tuple of (aabb_size, obb_size) as [x, y, z] lists
        """
        if len(vertices) == 0:
            return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]

        min_coords = np.min(vertices, axis=0)
        max_coords = np.max(vertices, axis=0)
        aabb_size = (max_coords - min_coords).tolist()

        # For OBB, use AABB as approximation (proper OBB would need PCA)
        obb_size = aabb_size.copy()

        return aabb_size, obb_size

    def _calculate_hole_area_ratio(
        self,
        vertices: NDArray[np.float64],
        triangles: NDArray[np.int64],
    ) -> float:
        """Calculate ratio of hole area to total surface area.

        This is a simplified estimation based on mesh boundary edges.

        Args:
            vertices: Vertex array (N, 3)
            triangles: Triangle index array (M, 3)

        Returns:
            Hole area ratio (0.0-1.0)
        """
        if HAS_TRIMESH:
            try:
                mesh = trimesh.Trimesh(vertices=vertices, faces=triangles)
                # Check if mesh is watertight (no holes)
                if mesh.is_watertight:
                    return 0.0
                # Estimate hole ratio based on boundary edges
                boundary_edges = len(mesh.edges_unique) - len(mesh.edges)
                if len(mesh.edges) > 0:
                    return min(1.0, boundary_edges / len(mesh.edges))
                return 0.0
            except Exception:
                return 0.0
        return 0.0

    def optimize(self) -> AssetMetrics:
        """Run full optimization pipeline.

        Returns:
            AssetMetrics with optimization results

        Raises:
            PipelineError: If optimization fails
        """
        logger.info("Starting asset optimization pipeline")
        start_time = time.time()

        # Load mesh
        vertices, triangles = self._load_mesh()

        # Normalize axes
        vertices = self.normalize_axes(vertices)

        # Apply scale
        vertices, scale_uncertainty = self.apply_scale(vertices)

        # Repair mesh
        vertices, triangles, non_manifold_edges = self.repair_mesh(vertices, triangles)

        # Calculate bounding box
        aabb_size, obb_size = self._calculate_bounding_box(vertices)

        # Generate LODs
        lod_metrics: list[LODMetrics] = []
        for level, target_tris in enumerate(self.LOD_LIMITS):
            lod_verts, lod_tris = self.generate_lod(vertices, triangles, target_tris)

            # Save LOD mesh
            lod_filename = f"lod{level}"
            lod_path = self.storage.save_asset_mesh(
                lod_verts, lod_tris, lod_filename, "glb"
            )

            # Get file size
            full_path = self.project_dir / lod_path
            file_size = full_path.stat().st_size if full_path.exists() else 0

            lod_metric = LODMetrics(
                level=level,
                triangles=len(lod_tris),
                vertices=len(lod_verts),
                file_size_bytes=file_size,
            )
            lod_metrics.append(lod_metric)
            logger.info(f"LOD{level}: {len(lod_tris)} triangles, {file_size} bytes")

        # Generate collision mesh
        coll_verts, coll_tris, num_convex_parts = self.generate_collision(vertices)
        if len(coll_tris) > 0:
            self.storage.save_asset_mesh(coll_verts, coll_tris, "collision", "obj")

        collision_metrics = CollisionMetrics(
            method="convex_hull",
            num_convex_parts=max(1, num_convex_parts),
            total_triangles=len(coll_tris),
        )

        # Generate preview
        preview_image = self.generate_preview(vertices, triangles)
        self.storage.save_preview_image(preview_image)

        # Calculate additional metrics
        hole_area_ratio = self._calculate_hole_area_ratio(vertices, triangles)

        processing_time = time.time() - start_time

        # Create metrics
        metrics = AssetMetrics(
            lod_metrics=lod_metrics,
            collision_metrics=collision_metrics,
            aabb_size=aabb_size,
            obb_size=obb_size,
            hole_area_ratio=hole_area_ratio,
            non_manifold_edges=non_manifold_edges,
            texture_resolution=self.DEFAULT_TEXTURE_RESOLUTION,
            texture_coverage=self.DEFAULT_TEXTURE_COVERAGE,
            scale_uncertainty=scale_uncertainty,
            gate_status="pending",
            gate_reasons=[],
        )

        # Save metrics
        self.storage.save_asset_metrics(metrics)

        logger.info(f"Asset optimization complete in {processing_time:.1f}s")

        return metrics
