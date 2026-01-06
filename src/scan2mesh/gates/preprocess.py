"""Preprocess quality gate.

This module provides the PreprocessQualityGate class for validating
preprocessing results.
"""

from scan2mesh.gates.thresholds import (
    PREPROCESS_MAX_MASK_AREA_RATIO,
    PREPROCESS_MIN_MASK_AREA_RATIO,
    PREPROCESS_MIN_VALID_FRAMES_RATIO,
    PREPROCESS_WARN_MASK_AREA_MIN,
    PREPROCESS_WARN_VALID_FRAMES_RATIO,
    QualityStatus,
)
from scan2mesh.models import PreprocessMetrics


class PreprocessQualityGate:
    """Quality gate for preprocessing stage.

    Validates preprocessing metrics against thresholds and provides
    suggestions for improvement.
    """

    def __init__(self) -> None:
        """Initialize PreprocessQualityGate."""
        self._reasons: list[str] = []
        self._suggestions: list[str] = []

    def validate(self, metrics: PreprocessMetrics) -> QualityStatus:
        """Validate preprocessing metrics against quality thresholds.

        Args:
            metrics: PreprocessMetrics to validate

        Returns:
            QualityStatus (PASS, WARN, or FAIL)
        """
        self._reasons = []
        self._suggestions = []

        # Check for no output frames
        if metrics.num_output_frames == 0:
            self._reasons.append("no_output_frames")
            self._suggestions.append(
                "No frames were processed successfully. "
                "Check that keyframes exist and raw frame data is valid."
            )
            return QualityStatus.FAIL

        # Check valid frames ratio
        if metrics.valid_frames_ratio < PREPROCESS_MIN_VALID_FRAMES_RATIO:
            self._reasons.append("low_valid_frames_ratio")
            self._suggestions.append(
                f"Valid frames ratio ({metrics.valid_frames_ratio:.1%}) is below threshold "
                f"({PREPROCESS_MIN_VALID_FRAMES_RATIO:.1%}). "
                "Check lighting conditions and object placement."
            )
            return QualityStatus.FAIL

        # Check mask area ratio minimum
        if metrics.mask_area_ratio_min < PREPROCESS_MIN_MASK_AREA_RATIO:
            self._reasons.append("mask_area_too_small")
            self._suggestions.append(
                f"Minimum mask area ratio ({metrics.mask_area_ratio_min:.1%}) is too small. "
                "The object may be too far from the camera or depth thresholds need adjustment."
            )
            return QualityStatus.FAIL

        # Check mask area ratio maximum
        if metrics.mask_area_ratio_mean > PREPROCESS_MAX_MASK_AREA_RATIO:
            self._reasons.append("mask_area_too_large")
            self._suggestions.append(
                f"Mean mask area ratio ({metrics.mask_area_ratio_mean:.1%}) is too large. "
                "The object may be too close or depth thresholds need adjustment."
            )
            return QualityStatus.FAIL

        # Warnings
        is_warn = False

        if metrics.valid_frames_ratio < PREPROCESS_WARN_VALID_FRAMES_RATIO:
            self._reasons.append("valid_frames_ratio_warn")
            self._suggestions.append(
                f"Valid frames ratio ({metrics.valid_frames_ratio:.1%}) is below optimal "
                f"({PREPROCESS_WARN_VALID_FRAMES_RATIO:.1%}). "
                "Consider recapturing with better lighting."
            )
            is_warn = True

        if metrics.mask_area_ratio_min < PREPROCESS_WARN_MASK_AREA_MIN:
            self._reasons.append("mask_area_min_warn")
            self._suggestions.append(
                f"Minimum mask area ratio ({metrics.mask_area_ratio_min:.1%}) is below optimal "
                f"({PREPROCESS_WARN_MASK_AREA_MIN:.1%}). "
                "Some frames may have poor segmentation."
            )
            is_warn = True

        if is_warn:
            return QualityStatus.WARN

        return QualityStatus.PASS

    def get_suggestions(self) -> list[str]:
        """Get improvement suggestions based on validation.

        Returns:
            List of suggestion strings
        """
        return self._suggestions.copy()

    def get_reasons(self) -> list[str]:
        """Get reasons for the quality status.

        Returns:
            List of reason identifiers
        """
        return self._reasons.copy()
