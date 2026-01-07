"""Reconstruct session models for managing 3D reconstruction state."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ReconstructStage(str, Enum):
    """Reconstruction pipeline stages."""

    IDLE = "idle"
    FEATURE_EXTRACTION = "feature_extraction"
    POSE_ESTIMATION = "pose_estimation"
    TSDF_FUSION = "tsdf_fusion"
    MESH_EXTRACTION = "mesh_extraction"
    TEXTURE_MAPPING = "texture_mapping"
    COMPLETE = "complete"


# Stage order for progress calculation
STAGE_ORDER: list[ReconstructStage] = [
    ReconstructStage.IDLE,
    ReconstructStage.FEATURE_EXTRACTION,
    ReconstructStage.POSE_ESTIMATION,
    ReconstructStage.TSDF_FUSION,
    ReconstructStage.MESH_EXTRACTION,
    ReconstructStage.TEXTURE_MAPPING,
    ReconstructStage.COMPLETE,
]


class ReconstructMetrics(BaseModel):
    """Metrics for a reconstruction result."""

    num_vertices: int = Field(default=0, ge=0, description="Number of mesh vertices")
    num_triangles: int = Field(default=0, ge=0, description="Number of mesh triangles")
    texture_resolution: tuple[int, int] = Field(
        default=(0, 0), description="Texture resolution (width, height)"
    )
    file_size_bytes: int = Field(default=0, ge=0, description="Output file size in bytes")
    is_watertight: bool = Field(default=False, description="Whether mesh is watertight")
    num_holes: int = Field(default=0, ge=0, description="Number of holes in mesh")
    surface_coverage: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Surface coverage ratio"
    )
    keyframes_used: int = Field(default=0, ge=0, description="Number of keyframes used")
    tracking_loss_frames: int = Field(
        default=0, ge=0, description="Number of frames with tracking loss"
    )


class ReconstructSession(BaseModel):
    """A reconstruction session managing the 3D reconstruction process."""

    session_id: str = Field(..., description="Unique session identifier")
    object_id: str = Field(..., description="ID of the object being reconstructed")
    input_frames: int = Field(
        default=0, ge=0, description="Number of input masked frames"
    )
    current_stage: ReconstructStage = Field(
        default=ReconstructStage.IDLE, description="Current reconstruction stage"
    )
    metrics: ReconstructMetrics = Field(default_factory=ReconstructMetrics)
    is_running: bool = Field(default=False, description="Whether reconstruction is active")
    output_mesh_path: str | None = Field(
        default=None, description="Path to output mesh file"
    )
    started_at: datetime | None = Field(
        default=None, description="When the session started"
    )

    @property
    def progress(self) -> float:
        """Get reconstruction progress as a ratio (0.0-1.0).

        Returns:
            Progress ratio based on current stage.
        """
        if self.current_stage == ReconstructStage.IDLE:
            return 0.0
        if self.current_stage == ReconstructStage.COMPLETE:
            return 1.0

        try:
            stage_index = STAGE_ORDER.index(self.current_stage)
            # Exclude IDLE and COMPLETE from calculation
            total_stages = len(STAGE_ORDER) - 2  # 5 working stages
            return stage_index / total_stages
        except ValueError:
            return 0.0

    @property
    def is_complete(self) -> bool:
        """Check if reconstruction is complete."""
        return self.current_stage == ReconstructStage.COMPLETE

    @property
    def can_proceed(self) -> bool:
        """Check if we can proceed to the next stage (Optimize)."""
        return self.is_complete and not self.is_running

    @property
    def stage_display_name(self) -> str:
        """Get human-readable name for current stage."""
        display_names = {
            ReconstructStage.IDLE: "Ready",
            ReconstructStage.FEATURE_EXTRACTION: "Extracting Features",
            ReconstructStage.POSE_ESTIMATION: "Estimating Camera Poses",
            ReconstructStage.TSDF_FUSION: "Building TSDF Volume",
            ReconstructStage.MESH_EXTRACTION: "Extracting Mesh",
            ReconstructStage.TEXTURE_MAPPING: "Generating Texture",
            ReconstructStage.COMPLETE: "Complete",
        }
        return display_names.get(self.current_stage, self.current_stage.value)
