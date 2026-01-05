"""Preprocessing data models.

This module defines models for masked frames and preprocessing methods.
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
