"""Reconstruction data models.

This module defines models for pose estimation and reconstruction reports.
"""

from pydantic import BaseModel, Field


class PoseEstimate(BaseModel):
    """Estimated camera pose for a frame.

    Attributes:
        frame_id: Frame identifier
        transformation: 4x4 transformation matrix (row-major)
        fitness: ICP fitness score (0.0-1.0)
        inlier_rmse: Inlier RMSE in meters
    """

    frame_id: int = Field(..., ge=0)
    transformation: list[list[float]]  # 4x4 matrix
    fitness: float = Field(..., ge=0.0, le=1.0)
    inlier_rmse: float = Field(..., ge=0)

    model_config = {"frozen": True}


class ReconReport(BaseModel):
    """Reconstruction report with metrics.

    Attributes:
        num_frames_used: Number of frames used in reconstruction
        tracking_success_rate: Ratio of successfully tracked frames (0.0-1.0)
        alignment_rmse_mean: Mean alignment RMSE in meters
        alignment_rmse_max: Maximum alignment RMSE in meters
        drift_indicator: Drift indicator in meters
        poses: List of estimated poses
        tsdf_voxel_size: TSDF voxel size in meters
        mesh_vertices: Number of mesh vertices
        mesh_triangles: Number of mesh triangles
        processing_time_sec: Total processing time in seconds
        gate_status: Quality gate status (pass, warn, fail)
        gate_reasons: Reasons for quality gate status
    """

    num_frames_used: int = Field(..., ge=0)
    tracking_success_rate: float = Field(..., ge=0.0, le=1.0)
    alignment_rmse_mean: float = Field(..., ge=0)
    alignment_rmse_max: float = Field(..., ge=0)
    drift_indicator: float = Field(..., ge=0)
    poses: list[PoseEstimate] = Field(default_factory=list)
    tsdf_voxel_size: float = Field(..., gt=0)
    mesh_vertices: int = Field(..., ge=0)
    mesh_triangles: int = Field(..., ge=0)
    processing_time_sec: float = Field(..., ge=0)
    gate_status: str = Field(default="pending")
    gate_reasons: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}
