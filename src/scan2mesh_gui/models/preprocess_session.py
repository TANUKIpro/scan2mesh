"""Preprocess session models for managing preprocessing state."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from scan2mesh_gui.models.capture_session import CapturedFrame


class MaskMethod(str, Enum):
    """Background removal method."""

    DEPTH_THRESHOLD = "depth_threshold"
    GRABCUT = "grabcut"
    U2NET = "u2net"


class MaskQuality(BaseModel):
    """Quality metrics for a generated mask."""

    mask_area_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Ratio of mask area to total area"
    )
    edge_quality: float = Field(
        ..., ge=0.0, le=1.0, description="Edge quality score (higher is better)"
    )
    is_valid: bool = Field(default=False, description="Whether the mask is valid")

    model_config = ConfigDict(frozen=True)


class MaskedFrame(BaseModel):
    """Metadata for a masked frame."""

    frame_id: int = Field(..., ge=0, description="Original frame index")
    method: MaskMethod = Field(..., description="Method used for masking")
    quality: MaskQuality
    mask_path: str | None = Field(default=None, description="Path to mask image")
    rgb_masked_path: str | None = Field(
        default=None, description="Path to masked RGB image"
    )
    depth_masked_path: str | None = Field(
        default=None, description="Path to masked depth image"
    )


class PreprocessMetrics(BaseModel):
    """Aggregated metrics for a preprocess session."""

    mask_area_ratio_mean: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean mask area ratio"
    )
    edge_quality_mean: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean edge quality"
    )
    num_processed: int = Field(default=0, ge=0, description="Number of processed frames")
    num_valid: int = Field(default=0, ge=0, description="Number of valid masks")


class PreprocessSession(BaseModel):
    """A preprocess session managing frame processing."""

    session_id: str = Field(..., description="Unique session identifier")
    object_id: str = Field(..., description="ID of the object being processed")
    captured_frames: list[CapturedFrame] = Field(
        default_factory=list, description="Input captured frames"
    )
    masked_frames: list[MaskedFrame] = Field(
        default_factory=list, description="Output masked frames"
    )
    metrics: PreprocessMetrics = Field(default_factory=PreprocessMetrics)
    is_running: bool = Field(default=False, description="Whether processing is active")
    started_at: datetime | None = Field(
        default=None, description="When the session started"
    )

    @property
    def total_frames(self) -> int:
        """Get total number of frames to process."""
        return len(self.captured_frames)

    @property
    def progress(self) -> float:
        """Get processing progress as a ratio (0.0-1.0)."""
        if self.total_frames <= 0:
            return 0.0
        return min(len(self.masked_frames) / self.total_frames, 1.0)

    @property
    def is_complete(self) -> bool:
        """Check if all frames have been processed."""
        return len(self.masked_frames) >= self.total_frames and self.total_frames > 0

    @property
    def can_proceed(self) -> bool:
        """Check if we can proceed to the next stage."""
        return self.is_complete and not self.is_running
