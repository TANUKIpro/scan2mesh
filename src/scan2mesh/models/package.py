"""Package result data models.

This module defines models for packaging stage results.
"""

from pydantic import BaseModel, Field


class PackageResult(BaseModel):
    """Result of the packaging stage.

    Attributes:
        manifest_path: Path to the generated manifest.json
        archive_path: Path to the generated ZIP archive
        output_dir: Path to the output bundle directory
        total_size_bytes: Total size of the archive in bytes
        files_included: List of files included in the package
    """

    manifest_path: str
    archive_path: str
    output_dir: str
    total_size_bytes: int = Field(..., ge=0)
    files_included: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}
