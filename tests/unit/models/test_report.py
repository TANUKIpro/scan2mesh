"""Tests for quality report data models."""

import pytest

from scan2mesh.models import QualityReport, StageQualitySummary


class TestStageQualitySummary:
    """Tests for StageQualitySummary model."""

    def test_create_with_pass_status(self) -> None:
        """Test creating a summary with PASS status."""
        summary = StageQualitySummary(
            stage_name="capture",
            status="pass",
            reasons=[],
        )
        assert summary.stage_name == "capture"
        assert summary.status == "pass"
        assert summary.reasons == []

    def test_create_with_fail_status_and_reasons(self) -> None:
        """Test creating a summary with FAIL status and reasons."""
        summary = StageQualitySummary(
            stage_name="reconstruct",
            status="fail",
            reasons=["Tracking success rate too low", "Drift indicator too high"],
        )
        assert summary.stage_name == "reconstruct"
        assert summary.status == "fail"
        assert len(summary.reasons) == 2
        assert "Tracking success rate too low" in summary.reasons

    def test_create_with_pending_status(self) -> None:
        """Test creating a summary with pending status."""
        summary = StageQualitySummary(
            stage_name="preprocess",
            status="pending",
            reasons=["Preprocess metrics not available"],
        )
        assert summary.stage_name == "preprocess"
        assert summary.status == "pending"

    def test_frozen_model(self) -> None:
        """Test that the model is immutable."""
        from pydantic import ValidationError

        summary = StageQualitySummary(
            stage_name="capture",
            status="pass",
        )
        with pytest.raises(ValidationError):
            summary.status = "fail"  # type: ignore[misc]


class TestQualityReport:
    """Tests for QualityReport model."""

    def test_create_with_all_stages_pass(self) -> None:
        """Test creating a report with all stages passing."""
        summaries = [
            StageQualitySummary(stage_name="capture", status="pass"),
            StageQualitySummary(stage_name="preprocess", status="pass"),
            StageQualitySummary(stage_name="reconstruct", status="pass"),
            StageQualitySummary(stage_name="optimize", status="pass"),
        ]
        report = QualityReport(
            project_name="test_ball",
            class_id=0,
            stage_summaries=summaries,
            overall_status="pass",
            available_stages=["capture", "preprocess", "reconstruct", "optimize"],
            missing_stages=[],
        )
        assert report.project_name == "test_ball"
        assert report.class_id == 0
        assert report.overall_status == "pass"
        assert len(report.stage_summaries) == 4
        assert len(report.available_stages) == 4
        assert len(report.missing_stages) == 0

    def test_create_with_mixed_status(self) -> None:
        """Test creating a report with mixed stage statuses."""
        summaries = [
            StageQualitySummary(stage_name="capture", status="pass"),
            StageQualitySummary(
                stage_name="preprocess",
                status="warn",
                reasons=["Mask area ratio low"],
            ),
            StageQualitySummary(stage_name="reconstruct", status="pass"),
            StageQualitySummary(
                stage_name="optimize",
                status="fail",
                reasons=["Too many holes"],
            ),
        ]
        report = QualityReport(
            project_name="complex_object",
            class_id=1,
            stage_summaries=summaries,
            overall_status="fail",
            overall_reasons=["Optimize stage failed", "Preprocess stage has warnings"],
            suggestions=["Capture additional frames to fill mesh holes"],
        )
        assert report.overall_status == "fail"
        assert len(report.overall_reasons) == 2
        assert len(report.suggestions) == 1

    def test_create_with_missing_stages(self) -> None:
        """Test creating a report with missing stages."""
        summaries = [
            StageQualitySummary(stage_name="capture", status="pass"),
            StageQualitySummary(
                stage_name="preprocess",
                status="pending",
                reasons=["Preprocess metrics not available"],
            ),
            StageQualitySummary(
                stage_name="reconstruct",
                status="pending",
                reasons=["Reconstruction metrics not available"],
            ),
            StageQualitySummary(
                stage_name="optimize",
                status="pending",
                reasons=["Asset metrics not available"],
            ),
        ]
        report = QualityReport(
            project_name="incomplete_project",
            class_id=2,
            stage_summaries=summaries,
            overall_status="pass",
            overall_reasons=[
                "Preprocess stage not completed",
                "Reconstruct stage not completed",
                "Optimize stage not completed",
            ],
            available_stages=["capture"],
            missing_stages=["preprocess", "reconstruct", "optimize"],
        )
        assert len(report.available_stages) == 1
        assert len(report.missing_stages) == 3

    def test_frozen_model(self) -> None:
        """Test that the model is immutable."""
        from pydantic import ValidationError

        report = QualityReport(
            project_name="test",
            class_id=0,
            stage_summaries=[],
            overall_status="pass",
        )
        with pytest.raises(ValidationError):
            report.overall_status = "fail"  # type: ignore[misc]
