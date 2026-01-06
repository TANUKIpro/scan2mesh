"""Reconstruction quality gate.

This module provides the ReconQualityGate class for validating reconstruction outputs.
"""

from scan2mesh.gates.thresholds import (
    RECON_MAX_ALIGNMENT_RMSE_PASS,
    RECON_MAX_ALIGNMENT_RMSE_WARN,
    RECON_MAX_DRIFT_INDICATOR_PASS,
    RECON_MAX_DRIFT_INDICATOR_WARN,
    RECON_MIN_MESH_TRIANGLES,
    RECON_MIN_TRACKING_SUCCESS_RATE_PASS,
    RECON_MIN_TRACKING_SUCCESS_RATE_WARN,
    QualityStatus,
    QualityThresholds,
)
from scan2mesh.models import ReconReport


class ReconQualityGate:
    """Quality gate for reconstruction stage outputs.

    Validates:
    - Tracking success rate (ratio of successfully tracked frames)
    - Alignment RMSE (pose estimation accuracy)
    - Drift indicator (cumulative error)
    - Mesh quality (minimum triangle count)

    Attributes:
        thresholds: Quality threshold configuration
    """

    def __init__(self, thresholds: QualityThresholds | None = None) -> None:
        """Initialize ReconQualityGate.

        Args:
            thresholds: Quality threshold configuration (uses defaults if None)
        """
        self.thresholds = thresholds or QualityThresholds()
        self._reasons: list[str] = []
        self._suggestions: list[str] = []
        self._status: QualityStatus = QualityStatus.PASS

    def validate(self, report: ReconReport) -> QualityStatus:
        """Validate reconstruction outputs against quality thresholds.

        Args:
            report: ReconReport with reconstruction metrics

        Returns:
            QualityStatus indicating PASS, WARN, or FAIL
        """
        self._reasons = []
        self._suggestions = []
        self._status = QualityStatus.PASS

        # Check tracking success rate
        self._check_tracking_success_rate(report.tracking_success_rate)

        # Check alignment RMSE
        self._check_alignment_rmse(report.alignment_rmse_mean)

        # Check drift indicator
        self._check_drift_indicator(report.drift_indicator)

        # Check mesh quality
        self._check_mesh_quality(report.mesh_triangles)

        return self._status

    def _check_tracking_success_rate(self, rate: float) -> None:
        """Check tracking success rate.

        Args:
            rate: Tracking success rate (0.0-1.0)
        """
        if rate >= RECON_MIN_TRACKING_SUCCESS_RATE_PASS:
            return  # PASS

        if rate >= RECON_MIN_TRACKING_SUCCESS_RATE_WARN:
            self._update_status(QualityStatus.WARN)
            self._reasons.append(
                f"tracking_success_rate_low: {rate:.1%} "
                f"(threshold: {RECON_MIN_TRACKING_SUCCESS_RATE_PASS:.0%})"
            )
            self._suggestions.append(
                "Some frames failed tracking. Consider recapturing with "
                "slower camera movement or better lighting."
            )
        else:
            self._update_status(QualityStatus.FAIL)
            self._reasons.append(
                f"tracking_success_rate_critical: {rate:.1%} "
                f"(threshold: {RECON_MIN_TRACKING_SUCCESS_RATE_WARN:.0%})"
            )
            self._suggestions.append(
                "Many frames failed tracking. Recapture with slower camera "
                "movement, ensure good lighting and texture on the object."
            )

    def _check_alignment_rmse(self, rmse: float) -> None:
        """Check alignment RMSE.

        Args:
            rmse: Mean alignment RMSE in meters
        """
        if rmse <= RECON_MAX_ALIGNMENT_RMSE_PASS:
            return  # PASS

        if rmse <= RECON_MAX_ALIGNMENT_RMSE_WARN:
            self._update_status(QualityStatus.WARN)
            self._reasons.append(
                f"alignment_rmse_high: {rmse:.4f}m "
                f"(threshold: {RECON_MAX_ALIGNMENT_RMSE_PASS:.4f}m)"
            )
            self._suggestions.append(
                "Pose estimation has moderate error. Consider capturing with "
                "more overlap between frames."
            )
        else:
            self._update_status(QualityStatus.FAIL)
            self._reasons.append(
                f"alignment_rmse_critical: {rmse:.4f}m "
                f"(threshold: {RECON_MAX_ALIGNMENT_RMSE_WARN:.4f}m)"
            )
            self._suggestions.append(
                "Pose estimation has high error. Recapture with more overlap "
                "between frames and ensure the object has enough texture."
            )

    def _check_drift_indicator(self, drift: float) -> None:
        """Check drift indicator.

        Args:
            drift: Drift indicator in meters
        """
        if drift <= RECON_MAX_DRIFT_INDICATOR_PASS:
            return  # PASS

        if drift <= RECON_MAX_DRIFT_INDICATOR_WARN:
            self._update_status(QualityStatus.WARN)
            self._reasons.append(
                f"drift_indicator_high: {drift:.4f}m "
                f"(threshold: {RECON_MAX_DRIFT_INDICATOR_PASS:.4f}m)"
            )
            self._suggestions.append(
                "Some camera drift detected. The resulting mesh may have "
                "slight misalignment."
            )
        else:
            self._update_status(QualityStatus.FAIL)
            self._reasons.append(
                f"drift_indicator_critical: {drift:.4f}m "
                f"(threshold: {RECON_MAX_DRIFT_INDICATOR_WARN:.4f}m)"
            )
            self._suggestions.append(
                "Significant camera drift detected. Recapture with slower "
                "camera movement and ensure loop closure."
            )

    def _check_mesh_quality(self, triangles: int) -> None:
        """Check mesh quality (triangle count).

        Args:
            triangles: Number of triangles in mesh
        """
        if triangles >= RECON_MIN_MESH_TRIANGLES:
            return  # PASS

        self._update_status(QualityStatus.FAIL)
        self._reasons.append(
            f"mesh_triangles_low: {triangles} "
            f"(threshold: {RECON_MIN_MESH_TRIANGLES})"
        )
        self._suggestions.append(
            "Mesh has too few triangles. Ensure the object is fully "
            "captured from all angles."
        )

    def _update_status(self, new_status: QualityStatus) -> None:
        """Update status to the more severe of current and new status.

        Args:
            new_status: New status to consider
        """
        # FAIL > WARN > PASS
        status_order = {
            QualityStatus.PASS: 0,
            QualityStatus.WARN: 1,
            QualityStatus.FAIL: 2,
        }

        if status_order[new_status] > status_order[self._status]:
            self._status = new_status

    def get_suggestions(self) -> list[str]:
        """Get improvement suggestions based on validation.

        Returns:
            List of suggestion strings
        """
        return self._suggestions.copy()

    def get_reasons(self) -> list[str]:
        """Get reasons for the quality status.

        Returns:
            List of reason strings
        """
        return self._reasons.copy()

    def get_report(self) -> dict[str, object]:
        """Generate detailed validation report.

        Returns:
            Dictionary containing validation details
        """
        return {
            "status": self._status.value,
            "reasons": self._reasons,
            "suggestions": self._suggestions,
            "thresholds": {
                "tracking_success_rate_pass": RECON_MIN_TRACKING_SUCCESS_RATE_PASS,
                "tracking_success_rate_warn": RECON_MIN_TRACKING_SUCCESS_RATE_WARN,
                "alignment_rmse_pass": RECON_MAX_ALIGNMENT_RMSE_PASS,
                "alignment_rmse_warn": RECON_MAX_ALIGNMENT_RMSE_WARN,
                "drift_indicator_pass": RECON_MAX_DRIFT_INDICATOR_PASS,
                "drift_indicator_warn": RECON_MAX_DRIFT_INDICATOR_WARN,
                "min_mesh_triangles": RECON_MIN_MESH_TRIANGLES,
            },
        }
