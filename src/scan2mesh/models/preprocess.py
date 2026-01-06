"""Preprocessing data models.

This module defines models for masked frames, preprocessing methods, and metrics.
"""

from enum import Enum

from pydantic import BaseModel, Field


class MaskMethod(str, Enum):
    """Background removal method types."""

    DEPTH_THRESHOLD = "depth_threshold"
    FLOOR_PLANE = "floor_plane"
    MANUAL_BOUNDING = "manual_bounding"


class MaskedFrame(BaseModel):
    """Data for a preprocessed (masked) frame.

    Attributes:
        frame_id: Original frame identifier
        rgb_masked_path: Path to masked RGB image
        depth_masked_path: Path to masked depth image
        mask_path: Path to mask image
        mask_method: Method used for masking
        mask_area_ratio: Ratio of masked area (0.0-1.0)
        is_valid: Whether the mask is valid for reconstruction
    """

    frame_id: int = Field(..., ge=0)
    rgb_masked_path: str
    depth_masked_path: str
    mask_path: str
    mask_method: MaskMethod
    mask_area_ratio: float = Field(..., ge=0.0, le=1.0)
    is_valid: bool = Field(default=True)

    model_config = {"frozen": True}


class PreprocessMetrics(BaseModel):
    """Metrics for a preprocessing session.

    Attributes:
        num_input_frames: Number of input keyframes
        num_output_frames: Number of successfully processed frames
        mask_method: Method used for masking
        mask_area_ratio_mean: Mean mask area ratio across frames
        mask_area_ratio_min: Minimum mask area ratio
        valid_frames_ratio: Ratio of valid output frames to input frames
        gate_status: Quality gate status (pass, warn, fail)
        gate_reasons: Reasons for quality gate status
    """

    num_input_frames: int = Field(..., ge=0)
    num_output_frames: int = Field(..., ge=0)
    mask_method: MaskMethod
    mask_area_ratio_mean: float = Field(..., ge=0.0, le=1.0)
    mask_area_ratio_min: float = Field(..., ge=0.0, le=1.0)
    valid_frames_ratio: float = Field(..., ge=0.0, le=1.0)
    gate_status: str = Field(default="pending")
    gate_reasons: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}
