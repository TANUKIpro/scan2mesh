"""Capture-related data models.

This module defines models for camera intrinsics, frames, capture plans, and metrics.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field


class CameraIntrinsics(BaseModel):
    """Camera intrinsic parameters.

    Attributes:
        width: Image width in pixels
        height: Image height in pixels
        fx: Focal length in x direction
        fy: Focal length in y direction
        cx: Principal point x coordinate
        cy: Principal point y coordinate
        depth_scale: Depth scale factor (meters per depth unit)
    """

    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    fx: float = Field(..., gt=0)
    fy: float = Field(..., gt=0)
    cx: float = Field(..., ge=0)
    cy: float = Field(..., ge=0)
    depth_scale: float = Field(..., gt=0)

    model_config = {"frozen": True}


class FrameQuality(BaseModel):
    """Quality metrics for a single frame.

    Attributes:
        depth_valid_ratio: Ratio of valid depth pixels (0.0-1.0)
        blur_score: Blur score (0.0-1.0, higher is sharper)
        object_occupancy: Object occupancy ratio in frame (0.0-1.0)
        is_keyframe: Whether this frame is selected as keyframe
    """

    depth_valid_ratio: float = Field(..., ge=0.0, le=1.0)
    blur_score: float = Field(..., ge=0.0, le=1.0)
    object_occupancy: float = Field(..., ge=0.0, le=1.0)
    is_keyframe: bool = Field(default=False)

    model_config = {"frozen": True}


class FrameData(BaseModel):
    """Data for a single captured frame.

    Attributes:
        frame_id: Unique frame identifier
        timestamp: Capture timestamp
        rgb_path: Path to RGB image file
        depth_path: Path to depth image file
        intrinsics: Camera intrinsic parameters
        quality: Frame quality metrics
        estimated_viewpoint: Estimated camera viewpoint (optional)
    """

    frame_id: int = Field(..., ge=0)
    timestamp: datetime
    rgb_path: str
    depth_path: str
    intrinsics: CameraIntrinsics
    quality: FrameQuality
    estimated_viewpoint: Optional["ViewPoint"] = None

    model_config = {"frozen": True}


class ViewPoint(BaseModel):
    """Camera viewpoint definition.

    Attributes:
        index: Viewpoint index number
        azimuth_deg: Azimuth angle in degrees (0-360)
        elevation_deg: Elevation angle in degrees (-90 to 90)
        distance_m: Distance from object in meters
        order: Capture order sequence number
    """

    index: int = Field(..., ge=0)
    azimuth_deg: float = Field(..., ge=0, lt=360)
    elevation_deg: float = Field(..., ge=-90, le=90)
    distance_m: float = Field(..., gt=0)
    order: int = Field(..., ge=0)

    model_config = {"frozen": True}


class CapturePlanPreset(str, Enum):
    """Capture plan preset types."""

    QUICK = "quick"  # 16-20 viewpoints
    STANDARD = "standard"  # 24-36 viewpoints
    HARD = "hard"  # Additional supplementary views


class CapturePlan(BaseModel):
    """Capture plan configuration.

    Attributes:
        preset: Capture plan preset type
        viewpoints: List of planned viewpoints
        min_required_frames: Minimum required keyframe count
        recommended_distance_m: Recommended capture distance
        notes: Capture notes and tips
    """

    preset: CapturePlanPreset
    viewpoints: list[ViewPoint]
    min_required_frames: int = Field(..., gt=0)
    recommended_distance_m: float = Field(..., gt=0)
    notes: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


class CaptureMetrics(BaseModel):
    """Metrics for a capture session.

    Attributes:
        num_frames_raw: Total number of captured frames
        num_keyframes: Number of selected keyframes
        depth_valid_ratio_mean: Mean depth valid ratio across keyframes
        depth_valid_ratio_min: Minimum depth valid ratio
        blur_score_mean: Mean blur score across keyframes
        blur_score_min: Minimum blur score
        coverage_score: Viewpoint coverage uniformity (0.0-1.0)
        capture_duration_sec: Total capture duration in seconds
        gate_status: Quality gate status (pass, warn, fail)
        gate_reasons: Reasons for quality gate status
    """

    num_frames_raw: int = Field(..., ge=0)
    num_keyframes: int = Field(..., ge=0)
    depth_valid_ratio_mean: float = Field(..., ge=0.0, le=1.0)
    depth_valid_ratio_min: float = Field(..., ge=0.0, le=1.0)
    blur_score_mean: float = Field(..., ge=0.0, le=1.0)
    blur_score_min: float = Field(..., ge=0.0, le=1.0)
    coverage_score: float = Field(..., ge=0.0, le=1.0)
    capture_duration_sec: float = Field(..., ge=0)
    gate_status: str = Field(default="pending")
    gate_reasons: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


class RawFrame:
    """Raw frame data from camera.

    This is a non-Pydantic class to hold numpy arrays efficiently.

    Attributes:
        rgb: RGB image as numpy array (H, W, 3), uint8
        depth: Depth image as numpy array (H, W), uint16 (mm)
        timestamp: Capture timestamp
        intrinsics: Camera intrinsic parameters
    """

    __slots__ = ("depth", "intrinsics", "rgb", "timestamp")

    def __init__(
        self,
        rgb: NDArray[np.uint8],
        depth: NDArray[np.uint16],
        timestamp: datetime,
        intrinsics: CameraIntrinsics,
    ) -> None:
        """Initialize RawFrame.

        Args:
            rgb: RGB image as numpy array (H, W, 3)
            depth: Depth image as numpy array (H, W)
            timestamp: Capture timestamp
            intrinsics: Camera intrinsic parameters
        """
        self.rgb = rgb
        self.depth = depth
        self.timestamp = timestamp
        self.intrinsics = intrinsics


class FramesMetadata(BaseModel):
    """Metadata for all captured frames.

    Attributes:
        frames: List of frame data
        total_frames: Total number of frames captured
        keyframe_ids: List of frame IDs selected as keyframes
    """

    frames: list[FrameData] = Field(default_factory=list)
    total_frames: int = Field(default=0)
    keyframe_ids: list[int] = Field(default_factory=list)
