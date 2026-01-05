"""Asset optimization data models.

This module defines models for LOD, collision, and asset metrics.
"""

from pydantic import BaseModel, Field


class LODMetrics(BaseModel):
    """Metrics for a Level of Detail mesh.

    Attributes:
        level: LOD level (0=highest detail, 2=lowest)
        triangles: Number of triangles
        vertices: Number of vertices
        file_size_bytes: File size in bytes
    """

    level: int = Field(..., ge=0, le=2)
    triangles: int = Field(..., ge=0)
    vertices: int = Field(..., ge=0)
    file_size_bytes: int = Field(..., ge=0)

    model_config = {"frozen": True}


class CollisionMetrics(BaseModel):
    """Metrics for collision mesh.

    Attributes:
        method: Collision mesh generation method (convex_hull, vhacd)
        num_convex_parts: Number of convex parts (for VHACD)
        total_triangles: Total triangle count
    """

    method: str  # "convex_hull" or "vhacd"
    num_convex_parts: int = Field(..., ge=1)
    total_triangles: int = Field(..., ge=0)

    model_config = {"frozen": True}


class AssetMetrics(BaseModel):
    """Metrics for optimized asset.

    Attributes:
        lod_metrics: Metrics for each LOD level
        collision_metrics: Collision mesh metrics
        aabb_size: Axis-aligned bounding box size [x, y, z] in meters
        obb_size: Oriented bounding box size [x, y, z] in meters
        hole_area_ratio: Ratio of hole area to surface area (0.0-1.0)
        non_manifold_edges: Number of non-manifold edges
        texture_resolution: Texture resolution in pixels
        texture_coverage: Texture coverage ratio (0.0-1.0)
        scale_uncertainty: Scale uncertainty level (low, medium, high)
        gate_status: Quality gate status (pass, warn, fail)
        gate_reasons: Reasons for quality gate status
    """

    lod_metrics: list[LODMetrics]
    collision_metrics: CollisionMetrics
    aabb_size: list[float]  # [x, y, z]
    obb_size: list[float]  # [x, y, z]
    hole_area_ratio: float = Field(..., ge=0.0, le=1.0)
    non_manifold_edges: int = Field(..., ge=0)
    texture_resolution: int = Field(..., gt=0)
    texture_coverage: float = Field(..., ge=0.0, le=1.0)
    scale_uncertainty: str  # "low", "medium", "high"
    gate_status: str = Field(default="pending")
    gate_reasons: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}
