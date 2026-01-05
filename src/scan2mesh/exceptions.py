"""Custom exceptions for scan2mesh.

Exception hierarchy:
    Scan2MeshError
    ├── ConfigError
    ├── CameraError
    ├── PipelineError
    │   └── QualityGateError
    ├── StorageError
    └── NotImplementedStageError
"""

from typing import Any


class Scan2MeshError(Exception):
    """Base exception for all scan2mesh errors."""

    pass


class ConfigError(Scan2MeshError):
    """Configuration related errors.

    Raised when:
    - Project configuration file is missing or invalid
    - Required fields are missing
    - Configuration validation fails
    """

    pass


class CameraError(Scan2MeshError):
    """Camera related errors.

    Raised when:
    - RealSense camera is not connected
    - Camera stream acquisition fails
    - Camera initialization fails
    """

    pass


class PipelineError(Scan2MeshError):
    """Pipeline processing errors.

    Raised when:
    - A pipeline stage fails to execute
    - Stage transition fails
    - Required data is missing
    """

    pass


class QualityGateError(PipelineError):
    """Quality gate failure.

    Raised when a quality gate evaluates to FAIL status.
    Contains metrics and suggestions for improvement.
    """

    def __init__(
        self,
        message: str,
        metrics: dict[str, Any] | None = None,
        suggestions: list[str] | None = None,
    ) -> None:
        """Initialize QualityGateError.

        Args:
            message: Error message describing the failure
            metrics: Dictionary of metrics that caused the failure
            suggestions: List of suggestions to fix the issue
        """
        super().__init__(message)
        self.metrics = metrics or {}
        self.suggestions = suggestions or []


class StorageError(Scan2MeshError):
    """Storage related errors.

    Raised when:
    - File read/write operations fail
    - Project directory operations fail
    - Data integrity checks fail
    """

    pass


class NotImplementedStageError(Scan2MeshError):
    """Raised when an unimplemented stage is called.

    Used for stub implementations during initial development.
    """

    pass
