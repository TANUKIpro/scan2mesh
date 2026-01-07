"""Capture session models for managing capture state."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FrameQuality(BaseModel):
    """Frame quality information."""

    depth_valid_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Ratio of valid depth pixels"
    )
    blur_score: float = Field(
        ..., ge=0.0, le=1.0, description="Sharpness score (higher is better)"
    )
    is_keyframe: bool = Field(default=False, description="Whether this is a keyframe")

    model_config = ConfigDict(frozen=True)


class CapturedFrame(BaseModel):
    """Metadata for a captured frame."""

    frame_id: int = Field(..., ge=0, description="Frame index")
    timestamp: datetime = Field(default_factory=datetime.now)
    quality: FrameQuality
    rgb_path: str | None = Field(default=None, description="Path to RGB image file")
    depth_path: str | None = Field(default=None, description="Path to depth image file")


class CaptureSessionMetrics(BaseModel):
    """Aggregated metrics for a capture session."""

    depth_valid_ratio_mean: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean depth valid ratio"
    )
    blur_score_mean: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean blur score"
    )
    coverage_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Coverage score"
    )
    num_frames: int = Field(default=0, ge=0, description="Total number of frames")
    num_keyframes: int = Field(default=0, ge=0, description="Number of keyframes")


class CaptureSession(BaseModel):
    """A capture session managing frame collection."""

    session_id: str = Field(..., description="Unique session identifier")
    object_id: str = Field(..., description="ID of the object being scanned")
    target_keyframes: int = Field(
        ..., ge=1, description="Target number of keyframes to capture"
    )
    frames: list[CapturedFrame] = Field(default_factory=list)
    metrics: CaptureSessionMetrics = Field(default_factory=CaptureSessionMetrics)
    is_running: bool = Field(default=False, description="Whether capture is active")
    started_at: datetime | None = Field(
        default=None, description="When the session started"
    )

    @property
    def progress(self) -> float:
        """Get capture progress as a ratio (0.0-1.0)."""
        if self.target_keyframes <= 0:
            return 0.0
        return min(self.metrics.num_frames / self.target_keyframes, 1.0)

    @property
    def is_complete(self) -> bool:
        """Check if the minimum frame requirement is met."""
        return self.metrics.num_frames >= 10  # Minimum frames required

    @property
    def can_proceed(self) -> bool:
        """Check if we can proceed to the next stage."""
        return self.is_complete and not self.is_running
