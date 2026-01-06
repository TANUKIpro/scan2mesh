"""Report service for generating quality reports."""

import uuid
from typing import TYPE_CHECKING

from scan2mesh_gui.models.config import QualityThresholds
from scan2mesh_gui.models.report_session import (
    ActionPriority,
    CaptureMetricsSummary,
    OptimizeMetricsSummary,
    PackageMetricsSummary,
    PreprocessMetricsSummary,
    QualityGateResult,
    RecommendedAction,
    ReconstructMetricsSummary,
    ReportSession,
)
from scan2mesh_gui.models.scan_object import QualityStatus


if TYPE_CHECKING:
    from scan2mesh_gui.models.capture_session import CaptureSession
    from scan2mesh_gui.models.optimize_session import OptimizeSession
    from scan2mesh_gui.models.package_session import PackageSession
    from scan2mesh_gui.models.preprocess_session import PreprocessSession
    from scan2mesh_gui.models.reconstruct_session import ReconstructSession
    from scan2mesh_gui.models.scan_object import ScanObject


class ReportService:
    """Service for generating quality reports from pipeline sessions."""

    def __init__(self, quality_thresholds: QualityThresholds) -> None:
        """Initialize the report service.

        Args:
            quality_thresholds: Quality threshold configuration.
        """
        self.thresholds = quality_thresholds

    def extract_capture_metrics(
        self, session: "CaptureSession | None"
    ) -> CaptureMetricsSummary | None:
        """Extract capture metrics from a capture session.

        Args:
            session: The capture session to extract metrics from.

        Returns:
            Capture metrics summary or None if session is not available.
        """
        if session is None:
            return None

        return CaptureMetricsSummary(
            num_keyframes=session.metrics.num_keyframes,
            depth_valid_ratio=session.metrics.depth_valid_ratio_mean,
            blur_score=session.metrics.blur_score_mean,
            coverage=session.metrics.coverage_score,
        )

    def extract_preprocess_metrics(
        self, session: "PreprocessSession | None"
    ) -> PreprocessMetricsSummary | None:
        """Extract preprocess metrics from a preprocess session.

        Args:
            session: The preprocess session to extract metrics from.

        Returns:
            Preprocess metrics summary or None if session is not available.
        """
        if session is None:
            return None

        return PreprocessMetricsSummary(
            num_frames_processed=session.metrics.num_processed,
            num_valid_masks=session.metrics.num_valid,
            mask_area_ratio_mean=session.metrics.mask_area_ratio_mean,
            edge_quality_mean=session.metrics.edge_quality_mean,
        )

    def extract_reconstruct_metrics(
        self, session: "ReconstructSession | None"
    ) -> ReconstructMetricsSummary | None:
        """Extract reconstruction metrics from a reconstruct session.

        Args:
            session: The reconstruct session to extract metrics from.

        Returns:
            Reconstruction metrics summary or None if session is not available.
        """
        if session is None:
            return None

        return ReconstructMetricsSummary(
            num_vertices=session.metrics.num_vertices,
            num_triangles=session.metrics.num_triangles,
            is_watertight=session.metrics.is_watertight,
            num_holes=session.metrics.num_holes,
            surface_coverage=session.metrics.surface_coverage,
            keyframes_used=session.metrics.keyframes_used,
            tracking_loss_frames=session.metrics.tracking_loss_frames,
            texture_resolution=session.metrics.texture_resolution,
        )

    def extract_optimize_metrics(
        self, session: "OptimizeSession | None"
    ) -> OptimizeMetricsSummary | None:
        """Extract optimization metrics from an optimize session.

        Args:
            session: The optimize session to extract metrics from.

        Returns:
            Optimization metrics summary or None if session is not available.
        """
        if session is None:
            return None

        return OptimizeMetricsSummary(
            scale_factor=session.metrics.scale_factor,
            holes_filled=session.metrics.holes_filled,
            components_removed=session.metrics.components_removed,
            lod0_triangles=session.metrics.lod0_triangles,
            lod1_triangles=session.metrics.lod1_triangles,
            lod2_triangles=session.metrics.lod2_triangles,
            collision_triangles=session.metrics.collision_triangles,
            texture_resolution=session.metrics.texture_resolution,
            bounding_box=session.metrics.bounding_box,
        )

    def extract_package_metrics(
        self, session: "PackageSession | None"
    ) -> PackageMetricsSummary | None:
        """Extract packaging metrics from a package session.

        Args:
            session: The package session to extract metrics from.

        Returns:
            Package metrics summary or None if session is not available.
        """
        if session is None:
            return None

        total_size_mb = session.metrics.total_size_bytes / (1024 * 1024)
        compressed_size_mb = None
        if session.metrics.compressed_size_bytes is not None:
            compressed_size_mb = session.metrics.compressed_size_bytes / (1024 * 1024)

        return PackageMetricsSummary(
            files_count=session.metrics.files_count,
            total_size_mb=total_size_mb,
            compressed_size_mb=compressed_size_mb,
            output_path=session.metrics.output_path,
        )

    def evaluate_quality_gates(
        self,
        capture_metrics: CaptureMetricsSummary | None,
        preprocess_metrics: PreprocessMetricsSummary | None,
        reconstruct_metrics: ReconstructMetricsSummary | None,
        optimize_metrics: OptimizeMetricsSummary | None,
    ) -> list[QualityGateResult]:
        """Evaluate quality gates based on metrics.

        Args:
            capture_metrics: Capture metrics summary.
            preprocess_metrics: Preprocess metrics summary.
            reconstruct_metrics: Reconstruction metrics summary.
            optimize_metrics: Optimization metrics summary.

        Returns:
            List of quality gate results.
        """
        gates: list[QualityGateResult] = []

        # Capture quality gates
        if capture_metrics:
            # Keyframes gate
            keyframes_status = (
                QualityStatus.PASS
                if capture_metrics.num_keyframes >= self.thresholds.min_keyframes
                else QualityStatus.FAIL
            )
            gates.append(
                QualityGateResult(
                    gate_name="Minimum Keyframes",
                    status=keyframes_status,
                    value=capture_metrics.num_keyframes,
                    threshold=f">= {self.thresholds.min_keyframes}",
                    reason=(
                        "Sufficient keyframes captured"
                        if keyframes_status == QualityStatus.PASS
                        else "Insufficient keyframes for quality reconstruction"
                    ),
                )
            )

            # Depth valid ratio gate
            depth_status = self._evaluate_threshold(
                capture_metrics.depth_valid_ratio,
                self.thresholds.depth_valid_ratio_warn,
                self.thresholds.depth_valid_ratio_fail,
            )
            gates.append(
                QualityGateResult(
                    gate_name="Depth Valid Ratio",
                    status=depth_status,
                    value=f"{capture_metrics.depth_valid_ratio:.2f}",
                    threshold=f">= {self.thresholds.depth_valid_ratio_fail}",
                    reason=self._get_depth_reason(depth_status),
                )
            )

            # Blur score gate
            blur_status = self._evaluate_threshold(
                capture_metrics.blur_score,
                self.thresholds.blur_score_warn,
                self.thresholds.blur_score_fail,
            )
            gates.append(
                QualityGateResult(
                    gate_name="Blur Score",
                    status=blur_status,
                    value=f"{capture_metrics.blur_score:.2f}",
                    threshold=f">= {self.thresholds.blur_score_fail}",
                    reason=self._get_blur_reason(blur_status),
                )
            )

            # Coverage gate
            coverage_status = self._evaluate_threshold(
                capture_metrics.coverage,
                self.thresholds.coverage_warn,
                self.thresholds.coverage_fail,
            )
            gates.append(
                QualityGateResult(
                    gate_name="Coverage",
                    status=coverage_status,
                    value=f"{capture_metrics.coverage:.2f}",
                    threshold=f">= {self.thresholds.coverage_fail}",
                    reason=self._get_coverage_reason(coverage_status),
                )
            )

        # Preprocess quality gates
        if preprocess_metrics:
            mask_ratio = (
                preprocess_metrics.num_valid_masks
                / preprocess_metrics.num_frames_processed
                if preprocess_metrics.num_frames_processed > 0
                else 0.0
            )
            mask_status = (
                QualityStatus.PASS
                if mask_ratio >= 0.9
                else QualityStatus.WARN
                if mask_ratio >= 0.7
                else QualityStatus.FAIL
            )
            gates.append(
                QualityGateResult(
                    gate_name="Mask Validity",
                    status=mask_status,
                    value=f"{mask_ratio:.2f}",
                    threshold=">= 0.9",
                    reason=(
                        "Most frames have valid masks"
                        if mask_status == QualityStatus.PASS
                        else "Some frames have invalid masks"
                        if mask_status == QualityStatus.WARN
                        else "Many frames have invalid masks"
                    ),
                )
            )

        # Reconstruction quality gates
        if reconstruct_metrics:
            # Watertight gate
            watertight_status = (
                QualityStatus.PASS
                if reconstruct_metrics.is_watertight
                else QualityStatus.WARN
            )
            gates.append(
                QualityGateResult(
                    gate_name="Mesh Watertight",
                    status=watertight_status,
                    value="Yes" if reconstruct_metrics.is_watertight else "No",
                    threshold="Yes",
                    reason=(
                        "Mesh is watertight"
                        if watertight_status == QualityStatus.PASS
                        else "Mesh has open boundaries"
                    ),
                )
            )

            # Tracking loss gate
            tracking_loss_ratio = (
                reconstruct_metrics.tracking_loss_frames
                / reconstruct_metrics.keyframes_used
                if reconstruct_metrics.keyframes_used > 0
                else 0.0
            )
            tracking_status = (
                QualityStatus.PASS
                if tracking_loss_ratio <= 0.05
                else QualityStatus.WARN
                if tracking_loss_ratio <= 0.15
                else QualityStatus.FAIL
            )
            gates.append(
                QualityGateResult(
                    gate_name="Tracking Quality",
                    status=tracking_status,
                    value=f"{reconstruct_metrics.tracking_loss_frames} frames",
                    threshold="<= 5% loss",
                    reason=(
                        "Tracking was stable"
                        if tracking_status == QualityStatus.PASS
                        else "Some tracking issues detected"
                        if tracking_status == QualityStatus.WARN
                        else "Significant tracking problems"
                    ),
                )
            )

        # Optimization quality gates
        if optimize_metrics:
            # LOD generation gate
            lod_status = (
                QualityStatus.PASS
                if (
                    optimize_metrics.lod0_triangles > 0
                    and optimize_metrics.lod1_triangles > 0
                    and optimize_metrics.lod2_triangles > 0
                )
                else QualityStatus.FAIL
            )
            gates.append(
                QualityGateResult(
                    gate_name="LOD Generation",
                    status=lod_status,
                    value="3 levels",
                    threshold="3 levels",
                    reason=(
                        "All LOD levels generated"
                        if lod_status == QualityStatus.PASS
                        else "Some LOD levels missing"
                    ),
                )
            )

        return gates

    def generate_recommendations(
        self, gates: list[QualityGateResult]
    ) -> list[RecommendedAction]:
        """Generate recommended actions based on quality gate results.

        Args:
            gates: List of quality gate results.

        Returns:
            List of recommended actions.
        """
        recommendations: list[RecommendedAction] = []

        for gate in gates:
            if gate.status == QualityStatus.FAIL:
                action = self._get_action_for_gate(gate.gate_name, is_fail=True)
                if action:
                    recommendations.append(action)
            elif gate.status == QualityStatus.WARN:
                action = self._get_action_for_gate(gate.gate_name, is_fail=False)
                if action:
                    recommendations.append(action)

        return recommendations

    def calculate_overall_status(
        self, gates: list[QualityGateResult]
    ) -> tuple[QualityStatus, str]:
        """Calculate overall quality status from gate results.

        Args:
            gates: List of quality gate results.

        Returns:
            Tuple of (overall status, status message).
        """
        if not gates:
            return QualityStatus.PENDING, "Quality evaluation pending"

        has_fail = any(g.status == QualityStatus.FAIL for g in gates)
        has_warn = any(g.status == QualityStatus.WARN for g in gates)

        if has_fail:
            fail_count = sum(1 for g in gates if g.status == QualityStatus.FAIL)
            return (
                QualityStatus.FAIL,
                f"Asset requires re-scanning ({fail_count} quality gates failed)",
            )
        elif has_warn:
            warn_count = sum(1 for g in gates if g.status == QualityStatus.WARN)
            return (
                QualityStatus.WARN,
                f"Asset has minor issues but is usable ({warn_count} warnings)",
            )
        else:
            return QualityStatus.PASS, "Asset is ready for distribution"

    def generate_report(
        self,
        scan_object: "ScanObject",
        capture_session: "CaptureSession | None" = None,
        preprocess_session: "PreprocessSession | None" = None,
        reconstruct_session: "ReconstructSession | None" = None,
        optimize_session: "OptimizeSession | None" = None,
        package_session: "PackageSession | None" = None,
    ) -> ReportSession:
        """Generate a complete quality report.

        Args:
            scan_object: The scanned object.
            capture_session: Optional capture session.
            preprocess_session: Optional preprocess session.
            reconstruct_session: Optional reconstruct session.
            optimize_session: Optional optimize session.
            package_session: Optional package session.

        Returns:
            Complete report session.
        """
        # Extract metrics from sessions
        capture_metrics = self.extract_capture_metrics(capture_session)
        preprocess_metrics = self.extract_preprocess_metrics(preprocess_session)
        reconstruct_metrics = self.extract_reconstruct_metrics(reconstruct_session)
        optimize_metrics = self.extract_optimize_metrics(optimize_session)
        package_metrics = self.extract_package_metrics(package_session)

        # Evaluate quality gates
        gates = self.evaluate_quality_gates(
            capture_metrics,
            preprocess_metrics,
            reconstruct_metrics,
            optimize_metrics,
        )

        # Generate recommendations
        recommendations = self.generate_recommendations(gates)

        # Calculate overall status
        overall_status, status_message = self.calculate_overall_status(gates)

        return ReportSession(
            session_id=str(uuid.uuid4()),
            object_id=scan_object.id,
            object_name=scan_object.name,
            display_name=scan_object.display_name,
            overall_status=overall_status,
            status_message=status_message,
            capture_metrics=capture_metrics,
            preprocess_metrics=preprocess_metrics,
            reconstruct_metrics=reconstruct_metrics,
            optimize_metrics=optimize_metrics,
            package_metrics=package_metrics,
            quality_gates=gates,
            recommendations=recommendations,
        )

    def _evaluate_threshold(
        self, value: float, warn_threshold: float, fail_threshold: float
    ) -> QualityStatus:
        """Evaluate a value against warn and fail thresholds.

        Args:
            value: The metric value.
            warn_threshold: Threshold below which status is WARN.
            fail_threshold: Threshold below which status is FAIL.

        Returns:
            Quality status based on value.
        """
        if value < fail_threshold:
            return QualityStatus.FAIL
        elif value < warn_threshold:
            return QualityStatus.WARN
        return QualityStatus.PASS

    def _get_depth_reason(self, status: QualityStatus) -> str:
        """Get reason string for depth quality status."""
        if status == QualityStatus.PASS:
            return "Depth data quality is good"
        elif status == QualityStatus.WARN:
            return "Some depth data quality issues"
        return "Significant depth data quality problems"

    def _get_blur_reason(self, status: QualityStatus) -> str:
        """Get reason string for blur quality status."""
        if status == QualityStatus.PASS:
            return "Images are sharp"
        elif status == QualityStatus.WARN:
            return "Some blurry images detected"
        return "Many blurry images detected"

    def _get_coverage_reason(self, status: QualityStatus) -> str:
        """Get reason string for coverage quality status."""
        if status == QualityStatus.PASS:
            return "Good coverage of object surface"
        elif status == QualityStatus.WARN:
            return "Some areas may be under-scanned"
        return "Insufficient coverage of object surface"

    def _get_action_for_gate(
        self, gate_name: str, is_fail: bool
    ) -> RecommendedAction | None:
        """Get recommended action for a specific gate failure or warning."""
        actions: dict[str, tuple[str, str, ActionPriority, ActionPriority]] = {
            "Minimum Keyframes": (
                "Capture more frames from different angles",
                "Consider capturing additional frames",
                ActionPriority.HIGH,
                ActionPriority.MEDIUM,
            ),
            "Depth Valid Ratio": (
                "Improve lighting and reduce reflective surfaces",
                "Check lighting conditions",
                ActionPriority.HIGH,
                ActionPriority.LOW,
            ),
            "Blur Score": (
                "Slow down camera movement and ensure stable capture",
                "Try to capture with steadier hands",
                ActionPriority.HIGH,
                ActionPriority.LOW,
            ),
            "Coverage": (
                "Capture from more angles to improve surface coverage",
                "Consider capturing more angles",
                ActionPriority.HIGH,
                ActionPriority.MEDIUM,
            ),
            "Mask Validity": (
                "Improve background contrast or adjust masking parameters",
                "Review masking settings",
                ActionPriority.MEDIUM,
                ActionPriority.LOW,
            ),
            "Mesh Watertight": (
                "Review mesh for holes and consider manual fixes",
                "Minor mesh issues may be acceptable",
                ActionPriority.MEDIUM,
                ActionPriority.LOW,
            ),
            "Tracking Quality": (
                "Re-scan with slower, more deliberate movements",
                "Consider re-scanning problematic areas",
                ActionPriority.HIGH,
                ActionPriority.MEDIUM,
            ),
            "LOD Generation": (
                "Check mesh quality and re-run optimization",
                "Review optimization settings",
                ActionPriority.HIGH,
                ActionPriority.MEDIUM,
            ),
        }

        if gate_name not in actions:
            return None

        fail_action, warn_action, fail_priority, warn_priority = actions[gate_name]

        # Determine target stage
        stage_map = {
            "Minimum Keyframes": "Capture",
            "Depth Valid Ratio": "Capture",
            "Blur Score": "Capture",
            "Coverage": "Capture",
            "Mask Validity": "Preprocess",
            "Mesh Watertight": "Reconstruct",
            "Tracking Quality": "Reconstruct",
            "LOD Generation": "Optimize",
        }

        return RecommendedAction(
            action=fail_action if is_fail else warn_action,
            priority=fail_priority if is_fail else warn_priority,
            target_stage=stage_map.get(gate_name, "Unknown"),
        )
