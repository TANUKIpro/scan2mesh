"""Tests for Reconstructor stage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from scan2mesh.models import PoseEstimate, ReconReport


class TestReconstructorInit:
    """Tests for Reconstructor initialization."""

    def test_init_basic(self, tmp_path: Path) -> None:
        """Test basic initialization."""
        from scan2mesh.stages.reconstruct import Reconstructor

        reconstructor = Reconstructor(tmp_path)
        assert reconstructor.project_dir == tmp_path
        assert reconstructor.voxel_size == Reconstructor.DEFAULT_VOXEL_SIZE
        assert reconstructor.sdf_trunc == Reconstructor.DEFAULT_SDF_TRUNC

    def test_init_with_custom_params(self, tmp_path: Path) -> None:
        """Test initialization with custom TSDF parameters."""
        from scan2mesh.stages.reconstruct import Reconstructor

        reconstructor = Reconstructor(
            tmp_path, voxel_size=0.005, sdf_trunc=0.02
        )
        assert reconstructor.voxel_size == 0.005
        assert reconstructor.sdf_trunc == 0.02


class TestCalculateDriftIndicator:
    """Tests for drift indicator calculation."""

    def test_drift_indicator_empty(self, tmp_path: Path) -> None:
        """Test drift indicator with no poses."""
        from scan2mesh.stages.reconstruct import Reconstructor

        reconstructor = Reconstructor(tmp_path)
        drift = reconstructor._calculate_drift_indicator([])
        assert drift == 0.0

    def test_drift_indicator_single_pose(self, tmp_path: Path) -> None:
        """Test drift indicator with single pose."""
        from scan2mesh.stages.reconstruct import Reconstructor

        reconstructor = Reconstructor(tmp_path)
        pose = PoseEstimate(
            frame_id=0,
            transformation=np.eye(4).tolist(),
            fitness=1.0,
            inlier_rmse=0.0,
        )
        drift = reconstructor._calculate_drift_indicator([pose])
        assert drift == 0.0

    def test_drift_indicator_multiple_poses(self, tmp_path: Path) -> None:
        """Test drift indicator with multiple poses."""
        from scan2mesh.stages.reconstruct import Reconstructor

        reconstructor = Reconstructor(tmp_path)

        # Create poses with known translations
        pose1 = PoseEstimate(
            frame_id=0,
            transformation=np.eye(4).tolist(),
            fitness=1.0,
            inlier_rmse=0.0,
        )

        trans2 = np.eye(4)
        trans2[0, 3] = 0.1  # 10cm in x
        pose2 = PoseEstimate(
            frame_id=1,
            transformation=trans2.tolist(),
            fitness=0.9,
            inlier_rmse=0.005,
        )

        trans3 = np.eye(4)
        trans3[0, 3] = 0.15  # 15cm in x
        pose3 = PoseEstimate(
            frame_id=2,
            transformation=trans3.tolist(),
            fitness=0.85,
            inlier_rmse=0.006,
        )

        drift = reconstructor._calculate_drift_indicator([pose1, pose2, pose3])

        # Max displacement should be 0.1 (from pose1 to pose2)
        assert abs(drift - 0.1) < 0.01


class TestReconstructorNoOpen3D:
    """Tests for Reconstructor when Open3D is not available."""

    def test_estimate_poses_without_open3d(self, tmp_path: Path) -> None:
        """Test that estimate_poses raises error without Open3D."""
        from scan2mesh.exceptions import ReconstructionError
        from scan2mesh.stages.reconstruct import Reconstructor

        with patch("scan2mesh.stages.reconstruct.HAS_OPEN3D", False):
            reconstructor = Reconstructor(tmp_path)
            with pytest.raises(ReconstructionError, match="Open3D is required"):
                reconstructor.estimate_poses()

    def test_integrate_frames_without_open3d(self, tmp_path: Path) -> None:
        """Test that integrate_frames raises error without Open3D."""
        from scan2mesh.exceptions import ReconstructionError
        from scan2mesh.stages.reconstruct import Reconstructor

        with patch("scan2mesh.stages.reconstruct.HAS_OPEN3D", False):
            reconstructor = Reconstructor(tmp_path)
            with pytest.raises(ReconstructionError, match="Open3D is required"):
                reconstructor.integrate_frames([])

    def test_extract_mesh_without_open3d(self, tmp_path: Path) -> None:
        """Test that extract_mesh raises error without Open3D."""
        from scan2mesh.exceptions import ReconstructionError
        from scan2mesh.stages.reconstruct import Reconstructor

        with patch("scan2mesh.stages.reconstruct.HAS_OPEN3D", False):
            reconstructor = Reconstructor(tmp_path)
            with pytest.raises(ReconstructionError, match="Open3D is required"):
                reconstructor.extract_mesh()


class TestReconstructorValidation:
    """Tests for Reconstructor input validation."""

    def test_estimate_poses_insufficient_keyframes(self, tmp_path: Path) -> None:
        """Test error when insufficient keyframes."""
        from scan2mesh.exceptions import ReconstructionError
        from scan2mesh.stages.reconstruct import Reconstructor

        # Mock storage and HAS_OPEN3D
        mock_storage = MagicMock()
        mock_metadata = MagicMock()
        mock_metadata.keyframe_ids = [0, 1]  # Only 2 keyframes
        mock_storage.load_frames_metadata.return_value = mock_metadata

        with patch("scan2mesh.stages.reconstruct.HAS_OPEN3D", True):
            reconstructor = Reconstructor(tmp_path, storage=mock_storage)
            with pytest.raises(ReconstructionError, match="at least"):
                reconstructor.estimate_poses()

    def test_integrate_frames_empty_poses(self, tmp_path: Path) -> None:
        """Test error when no poses provided."""
        from scan2mesh.exceptions import ReconstructionError
        from scan2mesh.stages.reconstruct import Reconstructor

        with patch("scan2mesh.stages.reconstruct.HAS_OPEN3D", True):
            reconstructor = Reconstructor(tmp_path)
            with pytest.raises(ReconstructionError, match="No poses provided"):
                reconstructor.integrate_frames([])

    def test_extract_mesh_no_volume(self, tmp_path: Path) -> None:
        """Test error when TSDF volume not initialized."""
        from scan2mesh.exceptions import ReconstructionError
        from scan2mesh.stages.reconstruct import Reconstructor

        with patch("scan2mesh.stages.reconstruct.HAS_OPEN3D", True):
            reconstructor = Reconstructor(tmp_path)
            with pytest.raises(ReconstructionError, match="TSDF volume not initialized"):
                reconstructor.extract_mesh()


class TestReconstructorGetCameraIntrinsics:
    """Tests for _get_camera_intrinsics method."""

    def test_get_camera_intrinsics_no_frames(self, tmp_path: Path) -> None:
        """Test error when no frames available."""
        from scan2mesh.exceptions import ReconstructionError
        from scan2mesh.stages.reconstruct import Reconstructor

        mock_storage = MagicMock()
        mock_metadata = MagicMock()
        mock_metadata.frames = []
        mock_storage.load_frames_metadata.return_value = mock_metadata

        reconstructor = Reconstructor(tmp_path, storage=mock_storage)
        with pytest.raises(ReconstructionError, match="No frames available"):
            reconstructor._get_camera_intrinsics()


class TestReconReport:
    """Tests for ReconReport model."""

    def test_recon_report_creation(self) -> None:
        """Test ReconReport can be created with valid data."""
        poses = [
            PoseEstimate(
                frame_id=0,
                transformation=np.eye(4).tolist(),
                fitness=1.0,
                inlier_rmse=0.0,
            )
        ]

        report = ReconReport(
            num_frames_used=10,
            tracking_success_rate=0.95,
            alignment_rmse_mean=0.005,
            alignment_rmse_max=0.01,
            drift_indicator=0.03,
            poses=poses,
            tsdf_voxel_size=0.002,
            mesh_vertices=5000,
            mesh_triangles=10000,
            processing_time_sec=30.5,
            gate_status="pass",
            gate_reasons=[],
        )

        assert report.num_frames_used == 10
        assert report.tracking_success_rate == 0.95
        assert len(report.poses) == 1
        assert report.mesh_vertices == 5000
