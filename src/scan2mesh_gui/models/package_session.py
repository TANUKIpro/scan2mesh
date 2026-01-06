"""Package session models for managing asset packaging state."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PackageStage(str, Enum):
    """Packaging pipeline stages."""

    IDLE = "idle"
    COLLECTING_ASSETS = "collecting_assets"
    GENERATING_MANIFEST = "generating_manifest"
    CREATING_ARCHIVE = "creating_archive"
    COMPLETE = "complete"


# Stage order for progress calculation
STAGE_ORDER: list[PackageStage] = [
    PackageStage.IDLE,
    PackageStage.COLLECTING_ASSETS,
    PackageStage.GENERATING_MANIFEST,
    PackageStage.CREATING_ARCHIVE,
    PackageStage.COMPLETE,
]


class PackageConfig(BaseModel):
    """Configuration for package creation."""

    output_format: str = Field(
        default="zip", description="Output format: 'directory' or 'zip'"
    )
    include_lod0: bool = Field(default=True, description="Include LOD0 mesh")
    include_lod1: bool = Field(default=True, description="Include LOD1 mesh")
    include_lod2: bool = Field(default=True, description="Include LOD2 mesh")
    include_collision: bool = Field(default=True, description="Include collision mesh")
    include_manifest: bool = Field(default=True, description="Include manifest.json")
    include_report: bool = Field(default=True, description="Include quality report")
    include_preview: bool = Field(default=True, description="Include preview images")
    include_source: bool = Field(default=False, description="Include source files")
    output_dir: str = Field(default="./output", description="Output directory path")


class PackageMetrics(BaseModel):
    """Metrics for a packaging result."""

    files_count: int = Field(default=0, ge=0, description="Number of files included")
    total_size_bytes: int = Field(
        default=0, ge=0, description="Total size in bytes (uncompressed)"
    )
    compressed_size_bytes: int | None = Field(
        default=None, description="Compressed size in bytes (ZIP only)"
    )
    output_path: str = Field(default="", description="Output file/directory path")
    files_included: list[str] = Field(
        default_factory=list, description="List of included file names"
    )


class PackageSession(BaseModel):
    """A packaging session managing the asset packaging process."""

    session_id: str = Field(..., description="Unique session identifier")
    object_id: str = Field(..., description="ID of the object being packaged")
    object_name: str = Field(..., description="Name of the object being packaged")
    current_stage: PackageStage = Field(
        default=PackageStage.IDLE, description="Current packaging stage"
    )
    config: PackageConfig = Field(default_factory=PackageConfig)
    metrics: PackageMetrics = Field(default_factory=PackageMetrics)
    is_running: bool = Field(default=False, description="Whether packaging is active")
    started_at: datetime | None = Field(
        default=None, description="When the session started"
    )

    @property
    def progress(self) -> float:
        """Get packaging progress as a ratio (0.0-1.0).

        Returns:
            Progress ratio based on current stage.
        """
        if self.current_stage == PackageStage.IDLE:
            return 0.0
        if self.current_stage == PackageStage.COMPLETE:
            return 1.0

        try:
            stage_index = STAGE_ORDER.index(self.current_stage)
            # Exclude IDLE and COMPLETE from calculation
            total_stages = len(STAGE_ORDER) - 2  # 3 working stages
            return stage_index / total_stages
        except ValueError:
            return 0.0

    @property
    def is_complete(self) -> bool:
        """Check if packaging is complete."""
        return self.current_stage == PackageStage.COMPLETE

    @property
    def can_proceed(self) -> bool:
        """Check if we can proceed to the next page (Report)."""
        return self.is_complete and not self.is_running

    @property
    def stage_display_name(self) -> str:
        """Get human-readable name for current stage."""
        display_names = {
            PackageStage.IDLE: "Ready",
            PackageStage.COLLECTING_ASSETS: "Collecting Assets",
            PackageStage.GENERATING_MANIFEST: "Generating Manifest",
            PackageStage.CREATING_ARCHIVE: "Creating Archive",
            PackageStage.COMPLETE: "Complete",
        }
        return display_names.get(self.current_stage, self.current_stage.value)
