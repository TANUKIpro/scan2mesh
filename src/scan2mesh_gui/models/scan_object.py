"""ScanObject model for tracking individual scan targets."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class PipelineStage(str, Enum):
    """Pipeline stages for scan processing."""

    INIT = "init"
    PLAN = "plan"
    CAPTURE = "capture"
    PREPROCESS = "preprocess"
    RECONSTRUCT = "reconstruct"
    OPTIMIZE = "optimize"
    PACKAGE = "package"
    REPORT = "report"


class QualityStatus(str, Enum):
    """Quality gate status."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    PENDING = "pending"


class ScanObject(BaseModel):
    """A scan target object with its metadata and pipeline state."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    profile_id: str
    name: str = Field(
        ..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"
    )
    display_name: str = Field(..., min_length=1, max_length=200)
    class_id: int = Field(..., ge=0, le=9999)
    tags: list[str] = Field(default_factory=list)
    known_dimension_mm: float | None = None
    dimension_type: str | None = None
    reference_images: list[str] = Field(default_factory=list)
    preview_image: str | None = None

    # Pipeline state
    current_stage: PipelineStage = PipelineStage.INIT
    quality_status: QualityStatus = QualityStatus.PENDING
    project_path: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_scan_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate object name for path safety."""
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid characters in name")
        return v

    @field_validator("dimension_type")
    @classmethod
    def validate_dimension_type(cls, v: str | None) -> str | None:
        """Validate dimension type."""
        allowed = {"diameter", "length", "width", "height"}
        if v is not None and v not in allowed:
            raise ValueError(f"dimension_type must be one of {allowed}")
        return v
