"""Tests for CaptureQualityGate."""

from scan2mesh.gates.capture import CaptureQualityGate
from scan2mesh.gates.thresholds import QualityStatus, QualityThresholds
from scan2mesh.models import CaptureMetrics


def create_metrics(
    num_frames_raw: int = 100,
    num_keyframes: int = 30,
    depth_valid_ratio_mean: float = 0.9,
    depth_valid_ratio_min: float = 0.8,
    blur_score_mean: float = 0.7,
    blur_score_min: float = 0.5,
    coverage_score: float = 0.85,
    capture_duration_sec: float = 60.0,
) -> CaptureMetrics:
    """Create CaptureMetrics with specified values."""
    return CaptureMetrics(
        num_frames_raw=num_frames_raw,
        num_keyframes=num_keyframes,
        depth_valid_ratio_mean=depth_valid_ratio_mean,
        depth_valid_ratio_min=depth_valid_ratio_min,
        blur_score_mean=blur_score_mean,
        blur_score_min=blur_score_min,
        coverage_score=coverage_score,
        capture_duration_sec=capture_duration_sec,
        gate_status="pending",
        gate_reasons=[],
    )


class TestCaptureQualityGateInit:
    """Tests for CaptureQualityGate initialization."""

    def test_init_default_thresholds(self) -> None:
        """Test initialization with default thresholds."""
        gate = CaptureQualityGate()
        assert gate.thresholds is not None
        assert gate.thresholds.capture_min_frames == 30

    def test_init_custom_thresholds(self) -> None:
        """Test initialization with custom thresholds."""
        thresholds = QualityThresholds(capture_min_frames=20)
        gate = CaptureQualityGate(thresholds=thresholds)
        assert gate.thresholds.capture_min_frames == 20


class TestValidatePass:
    """Tests for validation that should PASS."""

    def test_validate_good_metrics_passes(self) -> None:
        """Test that good metrics result in PASS."""
        gate = CaptureQualityGate()
        metrics = create_metrics()

        status = gate.validate(metrics)

        assert status == QualityStatus.PASS

    def test_validate_exactly_at_thresholds_passes(self) -> None:
        """Test metrics exactly at thresholds pass."""
        gate = CaptureQualityGate()
        metrics = create_metrics(
            num_keyframes=30,  # Exactly at minimum
            coverage_score=0.8,  # Exactly at minimum
            depth_valid_ratio_mean=0.7,  # Exactly at minimum
            blur_score_mean=0.5,  # Exactly at warning threshold
            blur_score_min=0.3,  # Exactly at fail threshold
        )

        status = gate.validate(metrics)

        assert status == QualityStatus.PASS


class TestValidateWarn:
    """Tests for validation that should WARN."""

    def test_validate_low_keyframes_warns(self) -> None:
        """Test that low keyframe count results in WARN."""
        gate = CaptureQualityGate()
        metrics = create_metrics(num_keyframes=20)  # Below 80% of 30

        status = gate.validate(metrics)

        assert status == QualityStatus.WARN
        assert "Keyframe count" in gate._reasons[0]

    def test_validate_low_coverage_warns(self) -> None:
        """Test that low coverage results in WARN."""
        gate = CaptureQualityGate()
        metrics = create_metrics(coverage_score=0.55)  # Below 80% of 0.8

        status = gate.validate(metrics)

        assert status == QualityStatus.WARN
        assert "Coverage" in gate._reasons[0]

    def test_validate_low_depth_ratio_warns(self) -> None:
        """Test that low depth valid ratio results in WARN."""
        gate = CaptureQualityGate()
        metrics = create_metrics(
            depth_valid_ratio_mean=0.6,  # Below 0.7
            depth_valid_ratio_min=0.5,  # Above fail threshold
        )

        status = gate.validate(metrics)

        assert status == QualityStatus.WARN
        assert "depth valid ratio" in gate._reasons[0]

    def test_validate_low_blur_score_warns(self) -> None:
        """Test that low mean blur score results in WARN."""
        gate = CaptureQualityGate()
        metrics = create_metrics(
            blur_score_mean=0.4,  # Below 0.5
            blur_score_min=0.35,  # Above fail threshold
        )

        status = gate.validate(metrics)

        assert status == QualityStatus.WARN
        assert "blur score" in gate._reasons[0]


class TestValidateFail:
    """Tests for validation that should FAIL."""

    def test_validate_very_low_keyframes_fails(self) -> None:
        """Test that very low keyframe count results in FAIL."""
        gate = CaptureQualityGate()
        metrics = create_metrics(num_keyframes=10)  # Below 50% of 30

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert "critically low" in gate._reasons[0]

    def test_validate_very_low_coverage_fails(self) -> None:
        """Test that very low coverage results in FAIL."""
        gate = CaptureQualityGate()
        metrics = create_metrics(coverage_score=0.3)  # Below 50% of 0.8

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert "Coverage" in gate._reasons[0]

    def test_validate_very_low_depth_ratio_fails(self) -> None:
        """Test that very low depth valid ratio results in FAIL."""
        gate = CaptureQualityGate()
        metrics = create_metrics(depth_valid_ratio_min=0.2)  # Below 50% of 0.7

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert "depth valid ratio" in gate._reasons[0]

    def test_validate_very_low_blur_score_fails(self) -> None:
        """Test that very low blur score results in FAIL."""
        gate = CaptureQualityGate()
        metrics = create_metrics(blur_score_min=0.2)  # Below 0.3

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert "blur score" in gate._reasons[0]

    def test_validate_multiple_failures(self) -> None:
        """Test that multiple failures are captured."""
        gate = CaptureQualityGate()
        metrics = create_metrics(
            num_keyframes=5,
            coverage_score=0.2,
            depth_valid_ratio_min=0.1,
            blur_score_min=0.1,
        )

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert len(gate._reasons) >= 3  # Multiple issues


class TestValidateStatusPriority:
    """Tests for status priority handling."""

    def test_fail_takes_priority_over_warn(self) -> None:
        """Test that FAIL status takes priority over WARN."""
        gate = CaptureQualityGate()
        metrics = create_metrics(
            num_keyframes=20,  # WARN level
            blur_score_min=0.2,  # FAIL level
        )

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL


class TestEvaluate:
    """Tests for evaluate method."""

    def test_evaluate_is_alias_for_validate(self) -> None:
        """Test that evaluate behaves same as validate."""
        gate = CaptureQualityGate()
        metrics = create_metrics()

        status1 = gate.validate(metrics)
        status2 = gate.evaluate(metrics)

        assert status1 == status2


class TestGetSuggestions:
    """Tests for get_suggestions method."""

    def test_get_suggestions_empty_after_pass(self) -> None:
        """Test that suggestions are empty after PASS."""
        gate = CaptureQualityGate()
        metrics = create_metrics()

        gate.validate(metrics)
        suggestions = gate.get_suggestions()

        assert suggestions == []

    def test_get_suggestions_after_warn(self) -> None:
        """Test that suggestions exist after WARN."""
        gate = CaptureQualityGate()
        metrics = create_metrics(num_keyframes=20)

        gate.validate(metrics)
        suggestions = gate.get_suggestions()

        assert len(suggestions) > 0

    def test_get_suggestions_returns_copy(self) -> None:
        """Test that get_suggestions returns a copy."""
        gate = CaptureQualityGate()
        metrics = create_metrics(num_keyframes=5)

        gate.validate(metrics)
        suggestions1 = gate.get_suggestions()
        suggestions2 = gate.get_suggestions()

        suggestions1.append("test")
        assert len(suggestions1) != len(suggestions2)


class TestGetReport:
    """Tests for get_report method."""

    def test_get_report_not_validated(self) -> None:
        """Test report before validation."""
        gate = CaptureQualityGate()
        report = gate.get_report()

        assert report["status"] == "not_validated"

    def test_get_report_after_validation(self) -> None:
        """Test report after validation."""
        gate = CaptureQualityGate()
        metrics = create_metrics()

        gate.validate(metrics)
        report = gate.get_report()

        assert report["status"] == "pass"
        assert "metrics" in report
        assert "thresholds" in report
        assert "reasons" in report
        assert "suggestions" in report

    def test_get_report_includes_metrics(self) -> None:
        """Test that report includes all metrics."""
        gate = CaptureQualityGate()
        metrics = create_metrics(
            num_frames_raw=50,
            num_keyframes=25,
        )

        gate.validate(metrics)
        report = gate.get_report()

        assert report["metrics"]["num_frames_raw"] == 50
        assert report["metrics"]["num_keyframes"] == 25

    def test_get_report_includes_thresholds(self) -> None:
        """Test that report includes thresholds."""
        gate = CaptureQualityGate()
        metrics = create_metrics()

        gate.validate(metrics)
        report = gate.get_report()

        assert "min_frames" in report["thresholds"]
        assert "min_coverage" in report["thresholds"]
        assert "min_depth_valid_ratio" in report["thresholds"]
        assert "min_blur_score" in report["thresholds"]

    def test_get_report_includes_reasons_and_suggestions(self) -> None:
        """Test that report includes reasons and suggestions for failures."""
        gate = CaptureQualityGate()
        metrics = create_metrics(num_keyframes=5)

        gate.validate(metrics)
        report = gate.get_report()

        assert len(report["reasons"]) > 0
        assert len(report["suggestions"]) > 0


class TestCustomThresholds:
    """Tests for custom threshold handling."""

    def test_custom_min_frames_affects_validation(self) -> None:
        """Test that custom min_frames threshold is used."""
        thresholds = QualityThresholds(capture_min_frames=10)
        gate = CaptureQualityGate(thresholds=thresholds)
        metrics = create_metrics(num_keyframes=8)  # Would fail with default 30

        status = gate.validate(metrics)

        # Should PASS or WARN with custom threshold of 10
        assert status != QualityStatus.FAIL
