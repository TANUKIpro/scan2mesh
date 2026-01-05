"""Capture quality gate.

This module provides the CaptureQualityGate class for validating capture outputs.
"""

from scan2mesh.exceptions import NotImplementedStageError
from scan2mesh.gates.thresholds import QualityStatus, QualityThresholds


class CaptureQualityGate:
    """Quality gate for capture stage outputs.

    Validates:
    - Frame count meets minimum requirements
    - Coverage is sufficient
    - Image quality (blur, exposure) is acceptable
    - Depth data validity

    Attributes:
        thresholds: Quality threshold configuration
    """

    def __init__(self, thresholds: QualityThresholds | None = None) -> None:
        """Initialize CaptureQualityGate.

        Args:
            thresholds: Quality threshold configuration (uses defaults if None)
        """
        self.thresholds = thresholds or QualityThresholds()

    def validate(self) -> QualityStatus:
        """Validate capture outputs against quality thresholds.

        Returns:
            QualityStatus indicating PASS, WARN, or FAIL

        Raises:
            NotImplementedStageError: This gate is not yet implemented
        """
        raise NotImplementedStageError("CaptureQualityGate.validate")

    def get_report(self) -> dict[str, object]:
        """Generate detailed validation report.

        Returns:
            Dictionary containing validation details

        Raises:
            NotImplementedStageError: This gate is not yet implemented
        """
        raise NotImplementedStageError("CaptureQualityGate.get_report")
