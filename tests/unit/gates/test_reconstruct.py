"""Tests for ReconQualityGate."""

import numpy as np

from scan2mesh.gates.reconstruct import ReconQualityGate
from scan2mesh.gates.thresholds import QualityStatus
from scan2mesh.models import PoseEstimate, ReconReport


def create_report(
    num_frames_used: int = 30,
    tracking_success_rate: float = 0.95,
    alignment_rmse_mean: float = 0.005,
    alignment_rmse_max: float = 0.01,
    drift_indicator: float = 0.02,
    mesh_vertices: int = 10000,
    mesh_triangles: int = 20000,
    processing_time_sec: float = 30.0,
    gate_status: str = "pending",
    gate_reasons: list[str] | None = None,
) -> ReconReport:
    """Create ReconReport with specified values."""
    poses = [
        PoseEstimate(
            frame_id=0,
            transformation=np.eye(4).tolist(),
            fitness=1.0,
            inlier_rmse=0.0,
        )
    ]
    return ReconReport(
        num_frames_used=num_frames_used,
        tracking_success_rate=tracking_success_rate,
        alignment_rmse_mean=alignment_rmse_mean,
        alignment_rmse_max=alignment_rmse_max,
        drift_indicator=drift_indicator,
        poses=poses,
        tsdf_voxel_size=0.002,
        mesh_vertices=mesh_vertices,
        mesh_triangles=mesh_triangles,
        processing_time_sec=processing_time_sec,
        gate_status=gate_status,
        gate_reasons=gate_reasons or [],
    )


class TestReconQualityGateInit:
    """Tests for ReconQualityGate initialization."""

    def test_init(self) -> None:
        """Test basic initialization."""
        gate = ReconQualityGate()
        assert gate._reasons == []
        assert gate._suggestions == []


class TestValidatePass:
    """Tests for validation that should PASS."""

    def test_validate_good_metrics_passes(self) -> None:
        """Test that good metrics result in PASS."""
        gate = ReconQualityGate()
        report = create_report()

        status = gate.validate(report)

        assert status == QualityStatus.PASS

    def test_validate_exactly_at_pass_thresholds_passes(self) -> None:
        """Test metrics exactly at pass thresholds."""
        gate = ReconQualityGate()
        report = create_report(
            tracking_success_rate=0.9,  # At pass threshold
            alignment_rmse_mean=0.01,  # At pass threshold
            drift_indicator=0.05,  # At pass threshold
        )

        status = gate.validate(report)

        assert status == QualityStatus.PASS


class TestValidateWarn:
    """Tests for validation that should WARN."""

    def test_validate_low_tracking_success_rate_warns(self) -> None:
        """Test that low tracking success rate results in WARN."""
        gate = ReconQualityGate()
        report = create_report(tracking_success_rate=0.8)  # Between 0.7 and 0.9

        status = gate.validate(report)

        assert status == QualityStatus.WARN
        assert len(gate._reasons) > 0
        assert "tracking_success_rate_low" in gate._reasons[0]

    def test_validate_high_alignment_rmse_warns(self) -> None:
        """Test that high alignment RMSE results in WARN."""
        gate = ReconQualityGate()
        report = create_report(alignment_rmse_mean=0.015)  # Between 0.01 and 0.02

        status = gate.validate(report)

        assert status == QualityStatus.WARN
        assert "alignment_rmse_high" in gate._reasons[0]

    def test_validate_high_drift_indicator_warns(self) -> None:
        """Test that high drift indicator results in WARN."""
        gate = ReconQualityGate()
        report = create_report(drift_indicator=0.08)  # Between 0.05 and 0.1

        status = gate.validate(report)

        assert status == QualityStatus.WARN
        assert "drift_indicator_high" in gate._reasons[0]


class TestValidateFail:
    """Tests for validation that should FAIL."""

    def test_validate_very_low_tracking_success_rate_fails(self) -> None:
        """Test that very low tracking success rate results in FAIL."""
        gate = ReconQualityGate()
        report = create_report(tracking_success_rate=0.5)  # Below 0.7

        status = gate.validate(report)

        assert status == QualityStatus.FAIL
        assert "tracking_success_rate_critical" in gate._reasons[0]

    def test_validate_very_high_alignment_rmse_fails(self) -> None:
        """Test that very high alignment RMSE results in FAIL."""
        gate = ReconQualityGate()
        report = create_report(alignment_rmse_mean=0.03)  # Above 0.02

        status = gate.validate(report)

        assert status == QualityStatus.FAIL
        assert "alignment_rmse_critical" in gate._reasons[0]

    def test_validate_very_high_drift_indicator_fails(self) -> None:
        """Test that very high drift indicator results in FAIL."""
        gate = ReconQualityGate()
        report = create_report(drift_indicator=0.15)  # Above 0.1

        status = gate.validate(report)

        assert status == QualityStatus.FAIL
        assert "drift_indicator_critical" in gate._reasons[0]

    def test_validate_low_mesh_triangles_fails(self) -> None:
        """Test that low mesh triangles results in FAIL."""
        gate = ReconQualityGate()
        report = create_report(mesh_triangles=500)  # Below 1000

        status = gate.validate(report)

        assert status == QualityStatus.FAIL
        assert "mesh_triangles_low" in gate._reasons[0]

    def test_validate_multiple_issues_fails(self) -> None:
        """Test that multiple issues result in FAIL with all reasons."""
        gate = ReconQualityGate()
        report = create_report(
            tracking_success_rate=0.5,  # FAIL
            alignment_rmse_mean=0.03,  # FAIL
            mesh_triangles=500,  # FAIL
        )

        status = gate.validate(report)

        assert status == QualityStatus.FAIL
        assert len(gate._reasons) == 3


class TestGetSuggestions:
    """Tests for get_suggestions method."""

    def test_get_suggestions_empty_after_pass(self) -> None:
        """Test that suggestions are empty after PASS."""
        gate = ReconQualityGate()
        report = create_report()

        gate.validate(report)
        suggestions = gate.get_suggestions()

        assert suggestions == []

    def test_get_suggestions_after_warn(self) -> None:
        """Test that suggestions exist after WARN."""
        gate = ReconQualityGate()
        report = create_report(tracking_success_rate=0.8)

        gate.validate(report)
        suggestions = gate.get_suggestions()

        assert len(suggestions) > 0

    def test_get_suggestions_after_fail(self) -> None:
        """Test that suggestions exist after FAIL."""
        gate = ReconQualityGate()
        report = create_report(tracking_success_rate=0.5)

        gate.validate(report)
        suggestions = gate.get_suggestions()

        assert len(suggestions) > 0

    def test_get_suggestions_returns_copy(self) -> None:
        """Test that get_suggestions returns a copy."""
        gate = ReconQualityGate()
        report = create_report(tracking_success_rate=0.5)

        gate.validate(report)
        suggestions1 = gate.get_suggestions()
        suggestions2 = gate.get_suggestions()

        suggestions1.append("test")
        assert len(suggestions1) != len(suggestions2)


class TestGetReasons:
    """Tests for get_reasons method."""

    def test_get_reasons_empty_after_pass(self) -> None:
        """Test that reasons are empty after PASS."""
        gate = ReconQualityGate()
        report = create_report()

        gate.validate(report)
        reasons = gate.get_reasons()

        assert reasons == []

    def test_get_reasons_after_fail(self) -> None:
        """Test that reasons exist after FAIL."""
        gate = ReconQualityGate()
        report = create_report(mesh_triangles=500)

        gate.validate(report)
        reasons = gate.get_reasons()

        assert len(reasons) > 0

    def test_get_reasons_returns_copy(self) -> None:
        """Test that get_reasons returns a copy."""
        gate = ReconQualityGate()
        report = create_report(mesh_triangles=500)

        gate.validate(report)
        reasons1 = gate.get_reasons()
        reasons2 = gate.get_reasons()

        reasons1.append("test")
        assert len(reasons1) != len(reasons2)


class TestGetReport:
    """Tests for get_report method."""

    def test_get_report_structure(self) -> None:
        """Test that get_report returns expected structure."""
        gate = ReconQualityGate()
        report = create_report(tracking_success_rate=0.8)

        gate.validate(report)
        gate_report = gate.get_report()

        assert "status" in gate_report
        assert "reasons" in gate_report
        assert "suggestions" in gate_report
        assert "thresholds" in gate_report

    def test_get_report_thresholds(self) -> None:
        """Test that get_report includes all thresholds."""
        gate = ReconQualityGate()
        report = create_report()

        gate.validate(report)
        gate_report = gate.get_report()

        thresholds = gate_report["thresholds"]
        assert "tracking_success_rate_pass" in thresholds  # type: ignore[operator]
        assert "tracking_success_rate_warn" in thresholds  # type: ignore[operator]
        assert "alignment_rmse_pass" in thresholds  # type: ignore[operator]
        assert "alignment_rmse_warn" in thresholds  # type: ignore[operator]
        assert "drift_indicator_pass" in thresholds  # type: ignore[operator]
        assert "drift_indicator_warn" in thresholds  # type: ignore[operator]
        assert "min_mesh_triangles" in thresholds  # type: ignore[operator]
