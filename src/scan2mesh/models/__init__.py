"""Data models for scan2mesh.

This module provides Pydantic models for all data structures used in the pipeline.
"""

from scan2mesh.models.asset import AssetMetrics, CollisionMetrics, LODMetrics
from scan2mesh.models.capture import (
    CameraIntrinsics,
    CaptureMetrics,
    CapturePlan,
    CapturePlanPreset,
    FrameData,
    FrameQuality,
    FramesMetadata,
    RawFrame,
    ViewPoint,
)
from scan2mesh.models.config import (
    CoordinateSystem,
    OutputPreset,
    ProjectConfig,
    ScaleInfo,
)
from scan2mesh.models.manifest import (
    AssetManifest,
    FileReferences,
    Provenance,
    QualityStatus,
)
from scan2mesh.models.package import PackageResult
from scan2mesh.models.preprocess import MaskedFrame, MaskMethod, PreprocessMetrics
from scan2mesh.models.reconstruct import PoseEstimate, ReconReport


__all__ = [
    "AssetManifest",
    "AssetMetrics",
    "CameraIntrinsics",
    "CaptureMetrics",
    "CapturePlan",
    "CapturePlanPreset",
    "CollisionMetrics",
    "CoordinateSystem",
    "FileReferences",
    "FrameData",
    "FrameQuality",
    "FramesMetadata",
    "LODMetrics",
    "MaskMethod",
    "MaskedFrame",
    "OutputPreset",
    "PackageResult",
    "PoseEstimate",
    "PreprocessMetrics",
    "ProjectConfig",
    "Provenance",
    "QualityStatus",
    "RawFrame",
    "ReconReport",
    "ScaleInfo",
    "ViewPoint",
]
