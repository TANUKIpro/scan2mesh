"""3D reconstruction stage.

This module provides the Reconstructor class for generating 3D meshes
from preprocessed RGBD frames using TSDF fusion.
"""

import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from scan2mesh.exceptions import ReconstructionError
from scan2mesh.models import CameraIntrinsics, PoseEstimate, ReconReport
from scan2mesh.services import StorageService


logger = logging.getLogger("scan2mesh.stages.reconstruct")

# Check for Open3D availability
try:
    import open3d as o3d

    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False
    o3d = None


class Reconstructor:
    """Reconstruct 3D mesh from preprocessed frames.

    This stage handles:
    - Camera pose estimation using RGBD odometry
    - TSDF volume integration
    - Mesh extraction using Marching Cubes
    - Quality metrics recording

    Attributes:
        project_dir: Path to the project directory
        storage: Storage service instance
        voxel_size: TSDF voxel size in meters
        sdf_trunc: TSDF truncation distance in meters
    """

    # Default TSDF parameters
    DEFAULT_VOXEL_SIZE = 0.002  # 2mm
    DEFAULT_SDF_TRUNC = 0.01  # 10mm

    # Odometry parameters
    ODOMETRY_MAX_DEPTH = 3.0  # meters
    ODOMETRY_MIN_DEPTH = 0.1  # meters

    # Tracking thresholds
    MIN_FITNESS_THRESHOLD = 0.3
    MIN_FRAMES_FOR_RECONSTRUCTION = 3

    def __init__(
        self,
        project_dir: Path,
        storage: StorageService | None = None,
        voxel_size: float = DEFAULT_VOXEL_SIZE,
        sdf_trunc: float = DEFAULT_SDF_TRUNC,
    ) -> None:
        """Initialize Reconstructor.

        Args:
            project_dir: Path to the project directory
            storage: Storage service instance (optional)
            voxel_size: TSDF voxel size in meters
            sdf_trunc: TSDF truncation distance in meters
        """
        self.project_dir = project_dir
        self.storage = storage or StorageService(project_dir)
        self.voxel_size = voxel_size
        self.sdf_trunc = sdf_trunc

        # State
        self._poses: list[PoseEstimate] = []
        self._volume: Any = None  # o3d.pipelines.integration.ScalableTSDFVolume
        self._mesh_vertices: NDArray[np.float64] | None = None
        self._mesh_triangles: NDArray[np.int64] | None = None

    def _get_camera_intrinsics(self) -> CameraIntrinsics:
        """Get camera intrinsics from frames metadata.

        Returns:
            CameraIntrinsics from the first frame

        Raises:
            ReconstructionError: If no frames are available
        """
        frames_metadata = self.storage.load_frames_metadata()
        if not frames_metadata.frames:
            raise ReconstructionError("No frames available in metadata")

        return frames_metadata.frames[0].intrinsics

    def _create_rgbd_image(
        self,
        rgb: NDArray[np.uint8],
        depth: NDArray[np.uint16],
        depth_scale: float = 1000.0,
    ) -> Any:
        """Create Open3D RGBD image from numpy arrays.

        Args:
            rgb: RGB image (H, W, 3)
            depth: Depth image (H, W) in mm
            depth_scale: Scale factor for depth (default 1000 for mm to m)

        Returns:
            Open3D RGBDImage
        """
        if not HAS_OPEN3D:
            raise ReconstructionError(
                "Open3D is required for reconstruction. Install with: uv add open3d"
            )

        color_o3d = o3d.geometry.Image(rgb)
        depth_o3d = o3d.geometry.Image(depth)

        rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
            color_o3d,
            depth_o3d,
            depth_scale=depth_scale,
            depth_trunc=self.ODOMETRY_MAX_DEPTH,
            convert_rgb_to_intensity=False,
        )

        return rgbd

    def _create_o3d_intrinsics(self, intrinsics: CameraIntrinsics) -> Any:
        """Create Open3D camera intrinsics.

        Args:
            intrinsics: CameraIntrinsics model

        Returns:
            Open3D PinholeCameraIntrinsic
        """
        if not HAS_OPEN3D:
            raise ReconstructionError("Open3D is required for reconstruction")

        return o3d.camera.PinholeCameraIntrinsic(
            width=intrinsics.width,
            height=intrinsics.height,
            fx=intrinsics.fx,
            fy=intrinsics.fy,
            cx=intrinsics.cx,
            cy=intrinsics.cy,
        )

    def estimate_poses(self) -> list[PoseEstimate]:
        """Estimate camera poses for all keyframes using RGBD odometry.

        Returns:
            List of PoseEstimate objects

        Raises:
            ReconstructionError: If pose estimation fails completely
        """
        if not HAS_OPEN3D:
            raise ReconstructionError(
                "Open3D is required for pose estimation. Install with: uv add open3d"
            )

        logger.info("Starting pose estimation")

        # Load frames metadata
        frames_metadata = self.storage.load_frames_metadata()
        keyframe_ids = frames_metadata.keyframe_ids

        if len(keyframe_ids) < self.MIN_FRAMES_FOR_RECONSTRUCTION:
            raise ReconstructionError(
                f"Need at least {self.MIN_FRAMES_FOR_RECONSTRUCTION} keyframes, "
                f"got {len(keyframe_ids)}"
            )

        # Get camera intrinsics
        intrinsics = self._get_camera_intrinsics()
        o3d_intrinsics = self._create_o3d_intrinsics(intrinsics)

        poses: list[PoseEstimate] = []
        prev_rgbd: Any = None
        cumulative_transform = np.eye(4)
        tracking_failures = 0

        # Create odometry option
        option = o3d.pipelines.odometry.OdometryOption()
        option.max_depth_diff = 0.07  # 7cm

        for i, frame_id in enumerate(keyframe_ids):
            try:
                # Load masked frame
                rgb, depth, _mask = self.storage.load_masked_frame_data(frame_id)

                # Create RGBD image
                current_rgbd = self._create_rgbd_image(
                    rgb, depth, intrinsics.depth_scale * 1000.0
                )

                if i == 0:
                    # First frame: identity transform
                    pose = PoseEstimate(
                        frame_id=frame_id,
                        transformation=cumulative_transform.tolist(),
                        fitness=1.0,
                        inlier_rmse=0.0,
                    )
                    poses.append(pose)
                    logger.debug(f"Frame {frame_id}: Reference frame (identity)")
                else:
                    # Compute odometry
                    success, trans, info = o3d.pipelines.odometry.compute_rgbd_odometry(
                        current_rgbd,
                        prev_rgbd,
                        o3d_intrinsics,
                        np.eye(4),
                        o3d.pipelines.odometry.RGBDOdometryJacobianFromHybridTerm(),
                        option,
                    )

                    if success:
                        # Extract fitness and RMSE from info
                        fitness = float(info[0, 0]) if info.shape[0] > 0 else 0.0
                        inlier_rmse = float(info[1, 1]) if info.shape[0] > 1 else 0.0

                        if fitness >= self.MIN_FITNESS_THRESHOLD:
                            # Update cumulative transform
                            cumulative_transform = cumulative_transform @ trans

                            pose = PoseEstimate(
                                frame_id=frame_id,
                                transformation=cumulative_transform.tolist(),
                                fitness=min(1.0, fitness),
                                inlier_rmse=inlier_rmse,
                            )
                            poses.append(pose)
                            logger.debug(
                                f"Frame {frame_id}: fitness={fitness:.3f}, "
                                f"rmse={inlier_rmse:.4f}"
                            )
                        else:
                            tracking_failures += 1
                            logger.warning(
                                f"Frame {frame_id}: Low fitness ({fitness:.3f}), skipping"
                            )
                    else:
                        tracking_failures += 1
                        logger.warning(f"Frame {frame_id}: Odometry failed, skipping")

                prev_rgbd = current_rgbd

            except Exception as e:
                tracking_failures += 1
                logger.error(f"Frame {frame_id}: Error - {e}")
                continue

        if len(poses) < self.MIN_FRAMES_FOR_RECONSTRUCTION:
            raise ReconstructionError(
                f"Only {len(poses)} frames tracked successfully, "
                f"need at least {self.MIN_FRAMES_FOR_RECONSTRUCTION}"
            )

        self._poses = poses
        logger.info(
            f"Pose estimation complete: {len(poses)}/{len(keyframe_ids)} frames tracked"
        )

        return poses

    def integrate_frames(self, poses: list[PoseEstimate]) -> None:
        """Integrate frames into TSDF volume.

        Args:
            poses: List of PoseEstimate with valid transformations

        Raises:
            ReconstructionError: If integration fails
        """
        if not HAS_OPEN3D:
            raise ReconstructionError("Open3D is required for TSDF integration")

        if not poses:
            raise ReconstructionError("No poses provided for integration")

        logger.info(f"Integrating {len(poses)} frames into TSDF volume")

        # Get camera intrinsics
        intrinsics = self._get_camera_intrinsics()
        o3d_intrinsics = self._create_o3d_intrinsics(intrinsics)

        # Create TSDF volume
        self._volume = o3d.pipelines.integration.ScalableTSDFVolume(
            voxel_length=self.voxel_size,
            sdf_trunc=self.sdf_trunc,
            color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8,
        )

        integrated_count = 0

        for pose in poses:
            try:
                # Load masked frame
                rgb, depth, _mask = self.storage.load_masked_frame_data(pose.frame_id)

                # Create RGBD image
                rgbd = self._create_rgbd_image(
                    rgb, depth, intrinsics.depth_scale * 1000.0
                )

                # Get transformation matrix
                extrinsic = np.array(pose.transformation)

                # Integrate into TSDF
                self._volume.integrate(
                    rgbd, o3d_intrinsics, np.linalg.inv(extrinsic)
                )
                integrated_count += 1

            except Exception as e:
                logger.warning(f"Failed to integrate frame {pose.frame_id}: {e}")
                continue

        if integrated_count == 0:
            raise ReconstructionError("No frames were integrated into TSDF volume")

        logger.info(f"TSDF integration complete: {integrated_count} frames integrated")

    def extract_mesh(self) -> tuple[int, int]:
        """Extract mesh from TSDF volume using Marching Cubes.

        Returns:
            Tuple of (num_vertices, num_triangles)

        Raises:
            ReconstructionError: If mesh extraction fails
        """
        if not HAS_OPEN3D:
            raise ReconstructionError("Open3D is required for mesh extraction")

        if self._volume is None:
            raise ReconstructionError("TSDF volume not initialized. Call integrate_frames first.")

        logger.info("Extracting mesh from TSDF volume")

        # Extract mesh
        mesh = self._volume.extract_triangle_mesh()

        # Clean up mesh
        mesh.compute_vertex_normals()
        mesh = mesh.remove_degenerate_triangles()
        mesh = mesh.remove_duplicated_triangles()
        mesh = mesh.remove_duplicated_vertices()
        mesh = mesh.remove_non_manifold_edges()

        # Get vertices and triangles as numpy arrays
        vertices = np.asarray(mesh.vertices)
        triangles = np.asarray(mesh.triangles)

        num_vertices = len(vertices)
        num_triangles = len(triangles)

        if num_triangles == 0:
            raise ReconstructionError("Mesh extraction produced empty mesh")

        # Store for later saving
        self._mesh_vertices = vertices.astype(np.float64)
        self._mesh_triangles = triangles.astype(np.int64)

        # Save mesh
        mesh_path = self.storage.save_mesh(self._mesh_vertices, self._mesh_triangles)
        logger.info(
            f"Mesh extracted: {num_vertices} vertices, {num_triangles} triangles"
        )
        logger.info(f"Mesh saved to: {mesh_path}")

        return num_vertices, num_triangles

    def _calculate_drift_indicator(self, poses: list[PoseEstimate]) -> float:
        """Calculate drift indicator from pose sequence.

        Uses the maximum translation distance between any two consecutive frames
        as an indicator of potential drift.

        Args:
            poses: List of PoseEstimate

        Returns:
            Drift indicator in meters
        """
        if len(poses) < 2:
            return 0.0

        max_displacement = 0.0

        for i in range(1, len(poses)):
            prev_trans = np.array(poses[i - 1].transformation)[:3, 3]
            curr_trans = np.array(poses[i].transformation)[:3, 3]
            displacement = float(np.linalg.norm(curr_trans - prev_trans))
            max_displacement = max(max_displacement, displacement)

        return float(max_displacement)

    def reconstruct(self) -> ReconReport:
        """Run full reconstruction pipeline.

        Returns:
            ReconReport with reconstruction metrics

        Raises:
            ReconstructionError: If reconstruction fails
        """
        logger.info("Starting full reconstruction pipeline")
        start_time = time.time()

        # Load frames metadata for total count
        frames_metadata = self.storage.load_frames_metadata()
        total_keyframes = len(frames_metadata.keyframe_ids)

        # Step 1: Estimate poses
        poses = self.estimate_poses()

        # Step 2: Integrate frames
        self.integrate_frames(poses)

        # Step 3: Extract mesh
        num_vertices, num_triangles = self.extract_mesh()

        # Calculate metrics
        processing_time = time.time() - start_time
        tracking_success_rate = len(poses) / total_keyframes if total_keyframes > 0 else 0.0

        # Calculate alignment RMSE statistics
        rmse_values = [p.inlier_rmse for p in poses if p.inlier_rmse > 0]
        alignment_rmse_mean = float(np.mean(rmse_values)) if rmse_values else 0.0
        alignment_rmse_max = float(np.max(rmse_values)) if rmse_values else 0.0

        # Calculate drift indicator
        drift_indicator = self._calculate_drift_indicator(poses)

        # Create report
        report = ReconReport(
            num_frames_used=len(poses),
            tracking_success_rate=tracking_success_rate,
            alignment_rmse_mean=alignment_rmse_mean,
            alignment_rmse_max=alignment_rmse_max,
            drift_indicator=drift_indicator,
            poses=poses,
            tsdf_voxel_size=self.voxel_size,
            mesh_vertices=num_vertices,
            mesh_triangles=num_triangles,
            processing_time_sec=processing_time,
            gate_status="pending",
            gate_reasons=[],
        )

        # Save report
        self.storage.save_recon_report(report)

        logger.info(
            f"Reconstruction complete in {processing_time:.1f}s: "
            f"{num_vertices} vertices, {num_triangles} triangles"
        )

        return report
