"""Optimize session models for managing mesh optimization state."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OptimizeStage(str, Enum):
    """Optimization pipeline stages."""

    IDLE = "idle"
    SCALE_CALIBRATION = "scale_calibration"
    MESH_CLEANING = "mesh_cleaning"
    LOD_GENERATION = "lod_generation"
    TEXTURE_OPTIMIZATION = "texture_optimization"
    COLLISION_MESH = "collision_mesh"
    COMPLETE = "complete"


# Stage order for progress calculation
STAGE_ORDER: list[OptimizeStage] = [
    OptimizeStage.IDLE,
    OptimizeStage.SCALE_CALIBRATION,
    OptimizeStage.MESH_CLEANING,
    OptimizeStage.LOD_GENERATION,
    OptimizeStage.TEXTURE_OPTIMIZATION,
    OptimizeStage.COLLISION_MESH,
    OptimizeStage.COMPLETE,
]


class OptimizeMetrics(BaseModel):
    """Metrics for an optimization result."""

    scale_factor: float = Field(
        default=1.0, ge=0.0, description="Applied scale factor"
    )
    holes_filled: int = Field(default=0, ge=0, description="Number of holes filled")
    components_removed: int = Field(
        default=0, ge=0, description="Number of isolated components removed"
    )
    lod0_triangles: int = Field(
        default=0, ge=0, description="LOD0 (highest detail) triangle count"
    )
    lod1_triangles: int = Field(
        default=0, ge=0, description="LOD1 (medium detail) triangle count"
    )
    lod2_triangles: int = Field(
        default=0, ge=0, description="LOD2 (low detail) triangle count"
    )
    collision_triangles: int = Field(
        default=0, ge=0, description="Collision mesh triangle count"
    )
    texture_resolution: tuple[int, int] = Field(
        default=(0, 0), description="Final texture resolution (width, height)"
    )
    output_size_bytes: int = Field(
        default=0, ge=0, description="Total output size in bytes"
    )
    bounding_box: tuple[float, float, float] = Field(
        default=(0.0, 0.0, 0.0), description="Bounding box dimensions (x, y, z) in meters"
    )


class OptimizeSession(BaseModel):
    """An optimization session managing the mesh optimization process."""

    session_id: str = Field(..., description="Unique session identifier")
    object_id: str = Field(..., description="ID of the object being optimized")
    input_mesh_path: str | None = Field(
        default=None, description="Path to input mesh file"
    )
    input_vertices: int = Field(default=0, ge=0, description="Input mesh vertex count")
    input_triangles: int = Field(
        default=0, ge=0, description="Input mesh triangle count"
    )
    current_stage: OptimizeStage = Field(
        default=OptimizeStage.IDLE, description="Current optimization stage"
    )
    metrics: OptimizeMetrics = Field(default_factory=OptimizeMetrics)
    is_running: bool = Field(default=False, description="Whether optimization is active")
    output_dir: str | None = Field(default=None, description="Output directory path")
    started_at: datetime | None = Field(
        default=None, description="When the session started"
    )

    # LOD configuration
    lod0_target: int = Field(default=100000, ge=0, description="Target LOD0 triangles")
    lod1_target: int = Field(default=30000, ge=0, description="Target LOD1 triangles")
    lod2_target: int = Field(default=10000, ge=0, description="Target LOD2 triangles")

    @property
    def progress(self) -> float:
        """Get optimization progress as a ratio (0.0-1.0).

        Returns:
            Progress ratio based on current stage.
        """
        if self.current_stage == OptimizeStage.IDLE:
            return 0.0
        if self.current_stage == OptimizeStage.COMPLETE:
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
        """Check if optimization is complete."""
        return self.current_stage == OptimizeStage.COMPLETE

    @property
    def can_proceed(self) -> bool:
        """Check if we can proceed to the next stage (Package)."""
        return self.is_complete and not self.is_running

    @property
    def stage_display_name(self) -> str:
        """Get human-readable name for current stage."""
        display_names = {
            OptimizeStage.IDLE: "Ready",
            OptimizeStage.SCALE_CALIBRATION: "Calibrating Scale",
            OptimizeStage.MESH_CLEANING: "Cleaning Mesh",
            OptimizeStage.LOD_GENERATION: "Generating LOD Levels",
            OptimizeStage.TEXTURE_OPTIMIZATION: "Optimizing Texture",
            OptimizeStage.COLLISION_MESH: "Creating Collision Mesh",
            OptimizeStage.COMPLETE: "Complete",
        }
        return display_names.get(self.current_stage, self.current_stage.value)
