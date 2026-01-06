"""Capture plan models for scan planning."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CapturePlanPreset(str, Enum):
    """Capture plan preset types."""

    QUICK = "quick"
    STANDARD = "standard"
    HIGH_QUALITY = "high_quality"


class ViewPoint(BaseModel):
    """A single viewpoint in the capture plan."""

    index: int = Field(..., ge=0, description="Viewpoint index")
    azimuth_deg: float = Field(..., ge=0, lt=360, description="Azimuth angle in degrees")
    elevation_deg: float = Field(
        ..., ge=-90, le=90, description="Elevation angle in degrees"
    )
    distance_m: float = Field(..., gt=0, description="Distance from object in meters")
    order: int = Field(..., ge=0, description="Capture order")

    model_config = {"frozen": True}


class CapturePlan(BaseModel):
    """A capture plan defining viewpoints for scanning."""

    preset: CapturePlanPreset
    viewpoints: list[ViewPoint] = Field(default_factory=list)
    min_required_frames: int = Field(..., ge=1, description="Minimum required frames")
    recommended_distance_m: float = Field(
        default=0.3, gt=0, description="Recommended distance in meters"
    )
    notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def num_viewpoints(self) -> int:
        """Get the number of viewpoints."""
        return len(self.viewpoints)

    @property
    def azimuth_positions(self) -> int:
        """Get the number of unique azimuth positions."""
        if not self.viewpoints:
            return 0
        return len({vp.azimuth_deg for vp in self.viewpoints})

    @property
    def elevation_levels(self) -> int:
        """Get the number of unique elevation levels."""
        if not self.viewpoints:
            return 0
        return len({vp.elevation_deg for vp in self.viewpoints})
