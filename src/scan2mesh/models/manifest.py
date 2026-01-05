"""Asset manifest data models.

This module defines models for the asset bundle manifest.
"""

from pydantic import BaseModel, Field

from scan2mesh.models.asset import AssetMetrics
from scan2mesh.models.capture import CaptureMetrics
from scan2mesh.models.config import CoordinateSystem, ScaleInfo
from scan2mesh.models.reconstruct import ReconReport


class Provenance(BaseModel):
    """Asset provenance information.

    Attributes:
        device: Capture device name
        tool_version: scan2mesh version used
        date: Creation date (ISO format)
        config_hash: Configuration hash for reproducibility
    """

    device: str
    tool_version: str
    date: str  # ISO format YYYY-MM-DD
    config_hash: str

    model_config = {"frozen": True}


class FileReferences(BaseModel):
    """References to asset files.

    Attributes:
        visual_lod0: Path to LOD0 visual mesh
        visual_lod1: Path to LOD1 visual mesh
        visual_lod2: Path to LOD2 visual mesh
        collision: Path to collision mesh
        preview: Path to preview image
    """

    visual_lod0: str
    visual_lod1: str
    visual_lod2: str
    collision: str
    preview: str

    model_config = {"frozen": True}


class QualityStatus(BaseModel):
    """Overall quality status.

    Attributes:
        status: Overall status (pass, warn, fail)
        reasons: List of reasons affecting the status
    """

    status: str  # "pass", "warn", "fail"
    reasons: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


class AssetManifest(BaseModel):
    """Complete asset bundle manifest.

    This is the main metadata file included in asset bundles.

    Attributes:
        schema_version: Manifest schema version
        object_name: Name of the scanned object
        class_id: Class ID for the object
        tags: Optional tags for categorization
        units: Output units
        coordinate_system: Coordinate system configuration
        scale: Scale information
        files: References to asset files
        quality: Overall quality status
        provenance: Asset provenance information
        capture_metrics: Capture session metrics
        recon_metrics: Reconstruction metrics
        asset_metrics: Asset optimization metrics
    """

    schema_version: str = Field(default="1.0")
    object_name: str
    class_id: int
    tags: list[str] = Field(default_factory=list)
    units: str
    coordinate_system: CoordinateSystem
    scale: ScaleInfo
    files: FileReferences
    quality: QualityStatus
    provenance: Provenance
    capture_metrics: CaptureMetrics
    recon_metrics: ReconReport
    asset_metrics: AssetMetrics

    model_config = {"frozen": True}
