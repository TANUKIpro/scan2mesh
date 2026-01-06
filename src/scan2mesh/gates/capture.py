"""Capture quality gate.

This module provides the CaptureQualityGate class for validating capture outputs.
"""

from scan2mesh.gates.thresholds import (
    CAPTURE_MIN_COVERAGE,
    CAPTURE_MIN_DEPTH_VALID_RATIO,
    QualityStatus,
    QualityThresholds,
)
from scan2mesh.models import CaptureMetrics


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

    # Threshold ratios for WARN vs FAIL
    WARN_RATIO = 0.8  # Below this ratio of threshold = WARN
    FAIL_RATIO = 0.5  # Below this ratio of threshold = FAIL

    # Blur score thresholds
    MIN_BLUR_SCORE = 0.3  # Minimum acceptable blur score (0-1)
    WARN_BLUR_SCORE = 0.5  # Warning threshold for blur score

    def __init__(self, thresholds: QualityThresholds | None = None) -> None:
        """Initialize CaptureQualityGate.

        Args:
            thresholds: Quality threshold configuration (uses defaults if None)
        """
        self.thresholds = thresholds or QualityThresholds()
        self._metrics: CaptureMetrics | None = None
        self._status: QualityStatus = QualityStatus.PASS
        self._reasons: list[str] = []
        self._suggestions: list[str] = []

    def validate(self, metrics: CaptureMetrics) -> QualityStatus:
        """Validate capture outputs against quality thresholds.

        Args:
            metrics: Capture metrics to validate

        Returns:
            QualityStatus indicating PASS, WARN, or FAIL
        """
        self._metrics = metrics
        self._reasons = []
        self._suggestions = []
        self._status = QualityStatus.PASS

        # Check frame count
        self._check_frame_count(metrics)

        # Check coverage
        self._check_coverage(metrics)

        # Check depth valid ratio
        self._check_depth_valid_ratio(metrics)

        # Check blur score
        self._check_blur_score(metrics)

        return self._status

    def _check_frame_count(self, metrics: CaptureMetrics) -> None:
        """Check if frame count meets requirements."""
        min_frames = self.thresholds.capture_min_frames

        if metrics.num_keyframes < min_frames * self.FAIL_RATIO:
            self._set_status(QualityStatus.FAIL)
            self._reasons.append(
                f"Keyframe count ({metrics.num_keyframes}) is critically low "
                f"(minimum: {min_frames})"
            )
            self._suggestions.append(
                "Capture more frames, ensuring good lighting and stable camera movement"
            )
        elif metrics.num_keyframes < min_frames * self.WARN_RATIO:
            self._set_status(QualityStatus.WARN)
            self._reasons.append(
                f"Keyframe count ({metrics.num_keyframes}) is below recommended "
                f"(minimum: {min_frames})"
            )
            self._suggestions.append(
                "Consider capturing a few more frames for better reconstruction"
            )

    def _check_coverage(self, metrics: CaptureMetrics) -> None:
        """Check if viewpoint coverage is sufficient."""
        min_coverage = CAPTURE_MIN_COVERAGE

        if metrics.coverage_score < min_coverage * self.FAIL_RATIO:
            self._set_status(QualityStatus.FAIL)
            self._reasons.append(
                f"Coverage ({metrics.coverage_score:.1%}) is critically low "
                f"(minimum: {min_coverage:.0%})"
            )
            self._suggestions.append(
                "Capture frames from more angles around the object (360° coverage recommended)"
            )
        elif metrics.coverage_score < min_coverage * self.WARN_RATIO:
            self._set_status(QualityStatus.WARN)
            self._reasons.append(
                f"Coverage ({metrics.coverage_score:.1%}) is below recommended "
                f"(minimum: {min_coverage:.0%})"
            )
            self._suggestions.append(
                "Try to capture from additional viewpoints for better coverage"
            )

    def _check_depth_valid_ratio(self, metrics: CaptureMetrics) -> None:
        """Check if depth data validity is acceptable."""
        min_depth_ratio = CAPTURE_MIN_DEPTH_VALID_RATIO

        if metrics.depth_valid_ratio_min < min_depth_ratio * self.FAIL_RATIO:
            self._set_status(QualityStatus.FAIL)
            self._reasons.append(
                f"Minimum depth valid ratio ({metrics.depth_valid_ratio_min:.1%}) is too low "
                f"(minimum: {min_depth_ratio:.0%})"
            )
            self._suggestions.append(
                "Ensure object is within camera depth range (0.3-1.0m) and avoid reflective surfaces"
            )
        elif metrics.depth_valid_ratio_mean < min_depth_ratio:
            self._set_status(QualityStatus.WARN)
            self._reasons.append(
                f"Mean depth valid ratio ({metrics.depth_valid_ratio_mean:.1%}) is below recommended "
                f"(minimum: {min_depth_ratio:.0%})"
            )
            self._suggestions.append(
                "Check for depth sensor occlusion or poor lighting conditions"
            )

    def _check_blur_score(self, metrics: CaptureMetrics) -> None:
        """Check if blur scores are acceptable."""
        if metrics.blur_score_min < self.MIN_BLUR_SCORE:
            self._set_status(QualityStatus.FAIL)
            self._reasons.append(
                f"Minimum blur score ({metrics.blur_score_min:.2f}) indicates severe motion blur"
            )
            self._suggestions.append(
                "Move the camera more slowly and ensure adequate lighting"
            )
        elif metrics.blur_score_mean < self.WARN_BLUR_SCORE:
            self._set_status(QualityStatus.WARN)
            self._reasons.append(
                f"Mean blur score ({metrics.blur_score_mean:.2f}) indicates some motion blur"
            )
            self._suggestions.append(
                "Consider slower camera movement for sharper images"
            )

    def _set_status(self, status: QualityStatus) -> None:
        """Set status, only upgrading severity (PASS -> WARN -> FAIL)."""
        if status == QualityStatus.FAIL:
            self._status = QualityStatus.FAIL
        elif status == QualityStatus.WARN and self._status != QualityStatus.FAIL:
            self._status = QualityStatus.WARN

    def evaluate(self, metrics: CaptureMetrics) -> QualityStatus:
        """Evaluate capture metrics and return status.

        Alias for validate() for consistency with other gates.

        Args:
            metrics: Capture metrics to evaluate

        Returns:
            QualityStatus indicating PASS, WARN, or FAIL
        """
        return self.validate(metrics)

    def get_suggestions(self) -> list[str]:
        """Get improvement suggestions based on last validation.

        Returns:
            List of suggestion strings
        """
        return self._suggestions.copy()

    def get_report(self) -> dict[str, object]:
        """Generate detailed validation report.

        Returns:
            Dictionary containing validation details
        """
        if self._metrics is None:
            return {
                "status": "not_validated",
                "message": "No metrics have been validated yet",
            }

        return {
            "status": self._status.value,
            "metrics": {
                "num_frames_raw": self._metrics.num_frames_raw,
                "num_keyframes": self._metrics.num_keyframes,
                "depth_valid_ratio_mean": self._metrics.depth_valid_ratio_mean,
                "depth_valid_ratio_min": self._metrics.depth_valid_ratio_min,
                "blur_score_mean": self._metrics.blur_score_mean,
                "blur_score_min": self._metrics.blur_score_min,
                "coverage_score": self._metrics.coverage_score,
                "capture_duration_sec": self._metrics.capture_duration_sec,
            },
            "thresholds": {
                "min_frames": self.thresholds.capture_min_frames,
                "min_coverage": CAPTURE_MIN_COVERAGE,
                "min_depth_valid_ratio": CAPTURE_MIN_DEPTH_VALID_RATIO,
                "min_blur_score": self.MIN_BLUR_SCORE,
            },
            "reasons": self._reasons,
            "suggestions": self._suggestions,
        }
