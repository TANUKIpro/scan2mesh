"""Project configuration models.

This module defines the core configuration models for scan2mesh projects.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CoordinateSystem(BaseModel):
    """Coordinate system configuration for output assets.

    Attributes:
        up_axis: The axis pointing upward (X, Y, or Z)
        forward_axis: The axis pointing forward (X, Y, or Z)
        origin: Origin point placement (bottom_center or centroid)
    """

    up_axis: str = Field(default="Z", pattern=r"^[XYZ]$")
    forward_axis: str = Field(default="Y", pattern=r"^[XYZ]$")
    origin: str = Field(default="bottom_center")

    model_config = {"frozen": True}


class OutputPreset(BaseModel):
    """Output preset configuration.

    Attributes:
        coordinate_system: Target coordinate system for output
        units: Output units (meter or millimeter)
        texture_resolution: Maximum texture resolution in pixels
        lod_triangle_limits: Triangle count limits for each LOD level
    """

    coordinate_system: CoordinateSystem = Field(default_factory=CoordinateSystem)
    units: str = Field(default="meter")
    texture_resolution: int = Field(default=2048, ge=256, le=4096)
    lod_triangle_limits: list[int] = Field(default=[100000, 30000, 10000])

    model_config = {"frozen": True}


class ScaleInfo(BaseModel):
    """Scale information for the scanned object.

    Attributes:
        method: Scale determination method (known_dimension or realsense_depth_scale)
        known_dimension_mm: Known dimension in millimeters (optional)
        dimension_type: Type of known dimension (diameter, length, width, height)
        uncertainty: Scale uncertainty level (low, medium, high)
    """

    method: str = Field(...)
    known_dimension_mm: float | None = Field(default=None, ge=0)
    dimension_type: str | None = Field(default=None)
    uncertainty: str = Field(default="medium")

    model_config = {"frozen": True}

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate scale method."""
        allowed = {"known_dimension", "realsense_depth_scale"}
        if v not in allowed:
            raise ValueError(f"method must be one of {allowed}")
        return v

    @field_validator("dimension_type")
    @classmethod
    def validate_dimension_type(cls, v: str | None) -> str | None:
        """Validate dimension type."""
        if v is not None:
            allowed = {"diameter", "length", "width", "height"}
            if v not in allowed:
                raise ValueError(f"dimension_type must be one of {allowed}")
        return v

    @field_validator("uncertainty")
    @classmethod
    def validate_uncertainty(cls, v: str) -> str:
        """Validate uncertainty level."""
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"uncertainty must be one of {allowed}")
        return v


class ProjectConfig(BaseModel):
    """Project configuration.

    This is the main configuration model stored in project.json.

    Attributes:
        schema_version: Configuration schema version
        object_name: Name of the scanned object
        class_id: Class ID for the object (0-9999)
        tags: Optional tags for categorization
        output_preset: Output configuration preset
        scale_info: Scale information (optional)
        created_at: Project creation timestamp
        updated_at: Last update timestamp
        config_hash: Hash of configuration for reproducibility
    """

    schema_version: str = Field(default="1.0")
    object_name: str = Field(
        ..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"
    )
    class_id: int = Field(..., ge=0, le=9999)
    tags: list[str] = Field(default_factory=list)
    output_preset: OutputPreset = Field(default_factory=OutputPreset)
    scale_info: ScaleInfo | None = Field(default=None)
    created_at: datetime
    updated_at: datetime
    config_hash: str = Field(...)

    @field_validator("object_name")
    @classmethod
    def validate_object_name(cls, v: str) -> str:
        """Validate object name for path traversal attacks."""
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError(
                "Invalid characters in object_name: path traversal detected"
            )
        return v

    model_config = {"frozen": True}

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tags."""
        for tag in v:
            if not tag or len(tag) > 50:
                raise ValueError("Each tag must be 1-50 characters")
        return v
