"""Tests for QualityReporter."""

import json
from pathlib import Path

import pytest

from scan2mesh.models import QualityReport, StageQualitySummary
from scan2mesh.stages.report import CollectedMetrics, QualityReporter


def create_project_config(project_dir: Path) -> None:
    """Create a valid project.json file."""
    config = {
        "schema_version": "1.0",
        "object_name": "test_object",
        "class_id": 42,
        "tags": ["test", "sample"],
        "output_preset": {
            "coordinate_system": {
                "up_axis": "Z",
                "forward_axis": "Y",
                "origin": "bottom_center",
            },
            "units": "meter",
            "texture_resolution": 2048,
            "lod_triangle_limits": [100000, 30000, 10000],
        },
        "scale_info": {
            "method": "known_dimension",
            "known_dimension_mm": 100.0,
            "dimension_type": "diameter",
            "uncertainty": "low",
        },
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
        "config_hash": "abc123def456",
    }
    (project_dir / "project.json").write_text(json.dumps(config))


def create_capture_metrics(project_dir: Path, gate_status: str = "pass") -> None:
    """Create capture_metrics.json file."""
    metrics = {
        "num_frames_raw": 30,
        "num_keyframes": 20,
        "depth_valid_ratio_mean": 0.9,
        "depth_valid_ratio_min": 0.8,
        "blur_score_mean": 0.85,
        "blur_score_min": 0.7,
        "coverage_score": 0.9,
        "capture_duration_sec": 60.0,
        "gate_status": gate_status,
        "gate_reasons": [] if gate_status == "pass" else ["Test reason"],
    }
    (project_dir / "capture_metrics.json").write_text(json.dumps(metrics))


def create_preprocess_metrics(project_dir: Path, gate_status: str = "pass") -> None:
    """Create preprocess_metrics.json file."""
    metrics = {
        "num_input_frames": 20,
        "num_output_frames": 18,
        "mask_method": "depth_threshold",
        "mask_area_ratio_mean": 0.25,
        "mask_area_ratio_min": 0.15,
        "valid_frames_ratio": 0.9,
        "gate_status": gate_status,
        "gate_reasons": [] if gate_status == "pass" else ["Test reason"],
    }
    (project_dir / "preprocess_metrics.json").write_text(json.dumps(metrics))


def create_recon_report(project_dir: Path, gate_status: str = "pass") -> None:
    """Create recon_report.json file."""
    report = {
        "num_frames_used": 20,
        "tracking_success_rate": 0.95,
        "alignment_rmse_mean": 0.005,
        "alignment_rmse_max": 0.01,
        "drift_indicator": 0.02,
        "poses": [],
        "tsdf_voxel_size": 0.002,
        "mesh_vertices": 50000,
        "mesh_triangles": 100000,
        "processing_time_sec": 120.0,
        "gate_status": gate_status,
        "gate_reasons": [] if gate_status == "pass" else ["Test reason"],
    }
    (project_dir / "recon_report.json").write_text(json.dumps(report))


def create_asset_metrics(project_dir: Path, gate_status: str = "pass") -> None:
    """Create asset_metrics.json file."""
    metrics = {
        "lod_metrics": [
            {"level": 0, "triangles": 100000, "vertices": 50000, "file_size_bytes": 1024000},
            {"level": 1, "triangles": 30000, "vertices": 15000, "file_size_bytes": 512000},
            {"level": 2, "triangles": 10000, "vertices": 5000, "file_size_bytes": 256000},
        ],
        "collision_metrics": {
            "method": "convex_hull",
            "num_convex_parts": 1,
            "total_triangles": 100,
        },
        "aabb_size": [0.1, 0.1, 0.1],
        "obb_size": [0.1, 0.1, 0.1],
        "hole_area_ratio": 0.01,
        "non_manifold_edges": 0,
        "texture_resolution": 2048,
        "texture_coverage": 0.95,
        "scale_uncertainty": "low",
        "gate_status": gate_status,
        "gate_reasons": [] if gate_status == "pass" else ["Test reason"],
    }
    (project_dir / "asset_metrics.json").write_text(json.dumps(metrics))


class TestCollectedMetrics:
    """Tests for CollectedMetrics container."""

    def test_create_empty(self) -> None:
        """Test creating empty metrics container."""
        metrics = CollectedMetrics()
        assert metrics.capture is None
        assert metrics.preprocess is None
        assert metrics.reconstruct is None
        assert metrics.asset is None

    def test_slots_defined(self) -> None:
        """Test that __slots__ is properly defined."""
        metrics = CollectedMetrics()
        assert hasattr(metrics, "__slots__")
        assert "capture" in metrics.__slots__
        assert "preprocess" in metrics.__slots__
        assert "reconstruct" in metrics.__slots__
        assert "asset" in metrics.__slots__


class TestCollectMetrics:
    """Tests for collect_metrics method."""

    def test_collect_all_metrics(self, tmp_path: Path) -> None:
        """Test collecting metrics when all files exist."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir)
        create_preprocess_metrics(project_dir)
        create_recon_report(project_dir)
        create_asset_metrics(project_dir)

        reporter = QualityReporter(project_dir)
        metrics = reporter.collect_metrics()

        assert metrics.capture is not None
        assert metrics.preprocess is not None
        assert metrics.reconstruct is not None
        assert metrics.asset is not None

    def test_collect_partial_metrics(self, tmp_path: Path) -> None:
        """Test collecting metrics when some files are missing."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir)
        # Missing preprocess, recon, and asset metrics

        reporter = QualityReporter(project_dir)
        metrics = reporter.collect_metrics()

        assert metrics.capture is not None
        assert metrics.preprocess is None
        assert metrics.reconstruct is None
        assert metrics.asset is None

    def test_collect_no_metrics(self, tmp_path: Path) -> None:
        """Test collecting metrics when no metric files exist."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)

        reporter = QualityReporter(project_dir)
        metrics = reporter.collect_metrics()

        assert metrics.capture is None
        assert metrics.preprocess is None
        assert metrics.reconstruct is None
        assert metrics.asset is None

    def test_collect_requires_project_config(self, tmp_path: Path) -> None:
        """Test that collect_metrics fails without project config."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        # No project.json

        reporter = QualityReporter(project_dir)
        from scan2mesh.exceptions import ConfigError
        with pytest.raises(ConfigError):
            reporter.collect_metrics()


class TestCalculateOverallStatus:
    """Tests for _calculate_overall_status method."""

    def test_all_pass_returns_pass(self, tmp_path: Path) -> None:
        """Test that all PASS statuses result in overall PASS."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)

        reporter = QualityReporter(project_dir)
        summaries = [
            StageQualitySummary(stage_name="capture", status="pass"),
            StageQualitySummary(stage_name="preprocess", status="pass"),
            StageQualitySummary(stage_name="reconstruct", status="pass"),
            StageQualitySummary(stage_name="optimize", status="pass"),
        ]

        status, reasons = reporter._calculate_overall_status(summaries)

        assert status == "pass"
        assert len(reasons) == 0

    def test_one_warn_returns_warn(self, tmp_path: Path) -> None:
        """Test that one WARN status results in overall WARN."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)

        reporter = QualityReporter(project_dir)
        summaries = [
            StageQualitySummary(stage_name="capture", status="warn"),
            StageQualitySummary(stage_name="preprocess", status="pass"),
            StageQualitySummary(stage_name="reconstruct", status="pass"),
            StageQualitySummary(stage_name="optimize", status="pass"),
        ]

        status, reasons = reporter._calculate_overall_status(summaries)

        assert status == "warn"
        assert len(reasons) == 1
        assert "Capture" in reasons[0]

    def test_one_fail_returns_fail(self, tmp_path: Path) -> None:
        """Test that one FAIL status results in overall FAIL."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)

        reporter = QualityReporter(project_dir)
        summaries = [
            StageQualitySummary(stage_name="capture", status="pass"),
            StageQualitySummary(stage_name="preprocess", status="fail"),
            StageQualitySummary(stage_name="reconstruct", status="pass"),
            StageQualitySummary(stage_name="optimize", status="pass"),
        ]

        status, reasons = reporter._calculate_overall_status(summaries)

        assert status == "fail"
        assert "Preprocess" in reasons[0]

    def test_fail_takes_precedence_over_warn(self, tmp_path: Path) -> None:
        """Test that FAIL takes precedence over WARN."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)

        reporter = QualityReporter(project_dir)
        summaries = [
            StageQualitySummary(stage_name="capture", status="warn"),
            StageQualitySummary(stage_name="preprocess", status="pass"),
            StageQualitySummary(stage_name="reconstruct", status="fail"),
            StageQualitySummary(stage_name="optimize", status="warn"),
        ]

        status, _reasons = reporter._calculate_overall_status(summaries)

        assert status == "fail"

    def test_pending_stages_noted_in_reasons(self, tmp_path: Path) -> None:
        """Test that pending stages are noted in reasons."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)

        reporter = QualityReporter(project_dir)
        summaries = [
            StageQualitySummary(stage_name="capture", status="pass"),
            StageQualitySummary(stage_name="preprocess", status="pending"),
            StageQualitySummary(stage_name="reconstruct", status="pending"),
            StageQualitySummary(stage_name="optimize", status="pending"),
        ]

        status, reasons = reporter._calculate_overall_status(summaries)

        assert status == "pass"
        assert len(reasons) == 3
        assert "Preprocess stage not completed" in reasons


class TestGenerateSuggestions:
    """Tests for _generate_suggestions method."""

    def test_no_suggestions_for_all_pass(self, tmp_path: Path) -> None:
        """Test that no suggestions are generated for all PASS."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir)
        create_preprocess_metrics(project_dir)
        create_recon_report(project_dir)
        create_asset_metrics(project_dir)

        reporter = QualityReporter(project_dir)
        metrics = reporter.collect_metrics()
        summaries = [
            StageQualitySummary(stage_name="capture", status="pass"),
            StageQualitySummary(stage_name="preprocess", status="pass"),
            StageQualitySummary(stage_name="reconstruct", status="pass"),
            StageQualitySummary(stage_name="optimize", status="pass"),
        ]

        suggestions = reporter._generate_suggestions(metrics, summaries)

        assert len(suggestions) == 0

    def test_suggestions_for_warn_status(self, tmp_path: Path) -> None:
        """Test that suggestions are generated for WARN status."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)

        # Create capture metrics with low coverage
        metrics_data = {
            "num_frames_raw": 30,
            "num_keyframes": 20,
            "depth_valid_ratio_mean": 0.9,
            "depth_valid_ratio_min": 0.8,
            "blur_score_mean": 0.85,
            "blur_score_min": 0.7,
            "coverage_score": 0.5,  # Low coverage
            "capture_duration_sec": 60.0,
            "gate_status": "warn",
            "gate_reasons": ["Low coverage"],
        }
        (project_dir / "capture_metrics.json").write_text(json.dumps(metrics_data))

        reporter = QualityReporter(project_dir)
        metrics = reporter.collect_metrics()
        summaries = [
            StageQualitySummary(stage_name="capture", status="warn"),
            StageQualitySummary(stage_name="preprocess", status="pending"),
            StageQualitySummary(stage_name="reconstruct", status="pending"),
            StageQualitySummary(stage_name="optimize", status="pending"),
        ]

        suggestions = reporter._generate_suggestions(metrics, summaries)

        assert len(suggestions) > 0
        assert any("coverage" in s.lower() for s in suggestions)


class TestGenerateReport:
    """Tests for generate_report method."""

    def test_generate_report_all_pass(self, tmp_path: Path) -> None:
        """Test generating report with all stages passing."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir, "pass")
        create_preprocess_metrics(project_dir, "pass")
        create_recon_report(project_dir, "pass")
        create_asset_metrics(project_dir, "pass")

        reporter = QualityReporter(project_dir)
        report = reporter.generate_report()

        assert isinstance(report, QualityReport)
        assert report.project_name == "test_object"
        assert report.class_id == 42
        assert report.overall_status == "pass"
        assert len(report.stage_summaries) == 4
        assert len(report.available_stages) == 4
        assert len(report.missing_stages) == 0

    def test_generate_report_mixed_status(self, tmp_path: Path) -> None:
        """Test generating report with mixed stage statuses."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir, "pass")
        create_preprocess_metrics(project_dir, "warn")
        create_recon_report(project_dir, "pass")
        create_asset_metrics(project_dir, "fail")

        reporter = QualityReporter(project_dir)
        report = reporter.generate_report()

        assert report.overall_status == "fail"
        assert len(report.overall_reasons) > 0

    def test_generate_report_missing_stages(self, tmp_path: Path) -> None:
        """Test generating report with missing stages."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir, "pass")
        # Missing preprocess, recon, and asset metrics

        reporter = QualityReporter(project_dir)
        report = reporter.generate_report()

        assert len(report.available_stages) == 1
        assert "capture" in report.available_stages
        assert len(report.missing_stages) == 3
        assert "preprocess" in report.missing_stages


class TestReport:
    """Tests for report method (main entry point)."""

    def test_report_returns_quality_report(self, tmp_path: Path) -> None:
        """Test that report() returns a QualityReport."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir)
        create_preprocess_metrics(project_dir)
        create_recon_report(project_dir)
        create_asset_metrics(project_dir)

        reporter = QualityReporter(project_dir)
        report = reporter.report()

        assert isinstance(report, QualityReport)
        assert report.project_name == "test_object"
        assert report.class_id == 42
