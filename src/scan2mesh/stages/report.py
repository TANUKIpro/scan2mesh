"""Quality reporting stage.

This module provides the QualityReporter class for generating quality reports.
"""

import contextlib
from pathlib import Path
from typing import ClassVar

from scan2mesh.exceptions import ConfigError
from scan2mesh.gates.thresholds import QualityStatus
from scan2mesh.models import (
    AssetMetrics,
    CaptureMetrics,
    PreprocessMetrics,
    QualityReport,
    ReconReport,
    StageQualitySummary,
)
from scan2mesh.services import StorageService


class CollectedMetrics:
    """Container for collected metrics from all stages.

    This is a non-Pydantic class to hold optional metrics.

    Attributes:
        capture: Capture metrics (optional)
        preprocess: Preprocess metrics (optional)
        reconstruct: Reconstruction report (optional)
        asset: Asset metrics (optional)
    """

    __slots__ = ("asset", "capture", "preprocess", "reconstruct")

    def __init__(
        self,
        capture: CaptureMetrics | None = None,
        preprocess: PreprocessMetrics | None = None,
        reconstruct: ReconReport | None = None,
        asset: AssetMetrics | None = None,
    ) -> None:
        """Initialize CollectedMetrics.

        Args:
            capture: Capture metrics (optional)
            preprocess: Preprocess metrics (optional)
            reconstruct: Reconstruction report (optional)
            asset: Asset metrics (optional)
        """
        self.capture = capture
        self.preprocess = preprocess
        self.reconstruct = reconstruct
        self.asset = asset


class QualityReporter:
    """Generate comprehensive quality reports.

    This stage handles:
    - Collecting metrics from all stages
    - Generating quality assessment reports
    - Creating improvement suggestions

    Attributes:
        project_dir: Path to the project directory
        storage: StorageService for file operations
    """

    # Stage names in pipeline order
    STAGE_NAMES: ClassVar[list[str]] = ["capture", "preprocess", "reconstruct", "optimize"]

    def __init__(
        self,
        project_dir: Path,
        storage: StorageService | None = None,
    ) -> None:
        """Initialize QualityReporter.

        Args:
            project_dir: Path to the project directory
            storage: Optional storage service (creates one if not provided)
        """
        self.project_dir = project_dir
        self.storage = storage or StorageService(project_dir)
        self._metrics: CollectedMetrics | None = None
        self._project_name: str = ""
        self._class_id: int = 0

    def collect_metrics(self) -> CollectedMetrics:
        """Collect metrics from all pipeline stages.

        Returns:
            CollectedMetrics containing available metrics

        Raises:
            ConfigError: If project config cannot be loaded
        """
        # Load project config first
        config = self.storage.load_project_config()
        self._project_name = config.object_name
        self._class_id = config.class_id

        # Collect metrics from each stage
        capture: CaptureMetrics | None = None
        preprocess: PreprocessMetrics | None = None
        reconstruct: ReconReport | None = None
        asset: AssetMetrics | None = None

        with contextlib.suppress(ConfigError):
            capture = self.storage.load_capture_metrics()

        with contextlib.suppress(ConfigError):
            preprocess = self.storage.load_preprocess_metrics()

        with contextlib.suppress(ConfigError):
            reconstruct = self.storage.load_recon_report()

        with contextlib.suppress(ConfigError):
            asset = self.storage.load_asset_metrics()

        self._metrics = CollectedMetrics(
            capture=capture,
            preprocess=preprocess,
            reconstruct=reconstruct,
            asset=asset,
        )
        return self._metrics

    def _get_stage_summary(
        self,
        stage_name: str,
        metrics: CollectedMetrics,
    ) -> StageQualitySummary:
        """Get quality summary for a single stage.

        Args:
            stage_name: Name of the stage
            metrics: Collected metrics

        Returns:
            StageQualitySummary for the stage
        """
        if stage_name == "capture":
            if metrics.capture is None:
                return StageQualitySummary(
                    stage_name=stage_name,
                    status="pending",
                    reasons=["Capture metrics not available"],
                )
            return StageQualitySummary(
                stage_name=stage_name,
                status=metrics.capture.gate_status,
                reasons=list(metrics.capture.gate_reasons),
            )

        elif stage_name == "preprocess":
            if metrics.preprocess is None:
                return StageQualitySummary(
                    stage_name=stage_name,
                    status="pending",
                    reasons=["Preprocess metrics not available"],
                )
            return StageQualitySummary(
                stage_name=stage_name,
                status=metrics.preprocess.gate_status,
                reasons=list(metrics.preprocess.gate_reasons),
            )

        elif stage_name == "reconstruct":
            if metrics.reconstruct is None:
                return StageQualitySummary(
                    stage_name=stage_name,
                    status="pending",
                    reasons=["Reconstruction metrics not available"],
                )
            return StageQualitySummary(
                stage_name=stage_name,
                status=metrics.reconstruct.gate_status,
                reasons=list(metrics.reconstruct.gate_reasons),
            )

        elif stage_name == "optimize":
            if metrics.asset is None:
                return StageQualitySummary(
                    stage_name=stage_name,
                    status="pending",
                    reasons=["Asset metrics not available"],
                )
            return StageQualitySummary(
                stage_name=stage_name,
                status=metrics.asset.gate_status,
                reasons=list(metrics.asset.gate_reasons),
            )

        else:
            return StageQualitySummary(
                stage_name=stage_name,
                status="pending",
                reasons=[f"Unknown stage: {stage_name}"],
            )

    def _calculate_overall_status(
        self,
        summaries: list[StageQualitySummary],
    ) -> tuple[str, list[str]]:
        """Calculate overall quality status from stage summaries.

        Args:
            summaries: List of stage quality summaries

        Returns:
            Tuple of (overall_status, overall_reasons)
        """
        overall_status = QualityStatus.PASS.value
        overall_reasons: list[str] = []

        for summary in summaries:
            if summary.status == QualityStatus.FAIL.value:
                overall_status = QualityStatus.FAIL.value
                overall_reasons.append(
                    f"{summary.stage_name.capitalize()} stage failed"
                )
            elif (
                summary.status == QualityStatus.WARN.value
                and overall_status != QualityStatus.FAIL.value
            ):
                overall_status = QualityStatus.WARN.value
                overall_reasons.append(
                    f"{summary.stage_name.capitalize()} stage has warnings"
                )
            elif summary.status == "pending":
                # Pending stages don't affect overall status but are noted
                overall_reasons.append(
                    f"{summary.stage_name.capitalize()} stage not completed"
                )

        return overall_status, overall_reasons

    def _generate_suggestions(
        self,
        metrics: CollectedMetrics,
        summaries: list[StageQualitySummary],
    ) -> list[str]:
        """Generate improvement suggestions based on metrics.

        Args:
            metrics: Collected metrics
            summaries: Stage quality summaries

        Returns:
            List of improvement suggestions
        """
        suggestions: list[str] = []

        for summary in summaries:
            if summary.status in [QualityStatus.FAIL.value, QualityStatus.WARN.value]:
                # Add stage-specific suggestions
                if summary.stage_name == "capture":
                    if metrics.capture is not None:
                        if metrics.capture.coverage_score < 0.8:
                            suggestions.append(
                                "Capture more frames from different angles "
                                "for better coverage"
                            )
                        if metrics.capture.blur_score_mean < 0.5:
                            suggestions.append(
                                "Move the camera more slowly to reduce motion blur"
                            )
                        if metrics.capture.depth_valid_ratio_mean < 0.7:
                            suggestions.append(
                                "Ensure the object is within the camera's depth range "
                                "(0.3-1.0m)"
                            )

                elif summary.stage_name == "preprocess":
                    if metrics.preprocess is not None:
                        if metrics.preprocess.mask_area_ratio_mean < 0.15:
                            suggestions.append(
                                "Adjust depth thresholds to capture more of the object"
                            )
                        if metrics.preprocess.valid_frames_ratio < 0.9:
                            suggestions.append(
                                "Re-capture frames that failed mask generation"
                            )

                elif summary.stage_name == "reconstruct":
                    if metrics.reconstruct is not None:
                        if metrics.reconstruct.tracking_success_rate < 0.9:
                            suggestions.append(
                                "Improve frame overlap by capturing with "
                                "slower camera movement"
                            )
                        if metrics.reconstruct.drift_indicator > 0.05:
                            suggestions.append(
                                "Reduce drift by ensuring more consistent lighting "
                                "and smoother camera motion"
                            )

                elif summary.stage_name == "optimize" and metrics.asset is not None:
                    if metrics.asset.hole_area_ratio > 0.01:
                        suggestions.append(
                            "Capture additional frames to fill mesh holes"
                        )
                    if metrics.asset.non_manifold_edges > 0:
                        suggestions.append(
                            "Consider re-running reconstruction with "
                            "higher quality settings"
                        )

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_suggestions: list[str] = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)

        return unique_suggestions

    def generate_report(self) -> QualityReport:
        """Generate quality assessment report.

        Returns:
            QualityReport containing the full assessment

        Raises:
            ConfigError: If metrics have not been collected
        """
        if self._metrics is None:
            self._metrics = self.collect_metrics()

        # Generate stage summaries
        summaries = [
            self._get_stage_summary(stage, self._metrics)
            for stage in self.STAGE_NAMES
        ]

        # Calculate overall status
        overall_status, overall_reasons = self._calculate_overall_status(summaries)

        # Generate suggestions
        suggestions = self._generate_suggestions(self._metrics, summaries)

        # Determine available and missing stages
        available_stages: list[str] = []
        missing_stages: list[str] = []

        if self._metrics.capture is not None:
            available_stages.append("capture")
        else:
            missing_stages.append("capture")

        if self._metrics.preprocess is not None:
            available_stages.append("preprocess")
        else:
            missing_stages.append("preprocess")

        if self._metrics.reconstruct is not None:
            available_stages.append("reconstruct")
        else:
            missing_stages.append("reconstruct")

        if self._metrics.asset is not None:
            available_stages.append("optimize")
        else:
            missing_stages.append("optimize")

        return QualityReport(
            project_name=self._project_name,
            class_id=self._class_id,
            stage_summaries=summaries,
            overall_status=overall_status,
            overall_reasons=overall_reasons,
            suggestions=suggestions,
            available_stages=available_stages,
            missing_stages=missing_stages,
        )

    def report(self) -> QualityReport:
        """Run full reporting pipeline.

        Returns:
            QualityReport containing the full assessment
        """
        self.collect_metrics()
        return self.generate_report()
