"""Tests for PreprocessQualityGate."""

from scan2mesh.gates.preprocess import PreprocessQualityGate
from scan2mesh.gates.thresholds import QualityStatus
from scan2mesh.models import MaskMethod, PreprocessMetrics


def create_metrics(
    num_input_frames: int = 30,
    num_output_frames: int = 28,
    mask_method: MaskMethod = MaskMethod.DEPTH_THRESHOLD,
    mask_area_ratio_mean: float = 0.4,
    mask_area_ratio_min: float = 0.2,
    valid_frames_ratio: float = 0.9,
    gate_status: str = "pending",
    gate_reasons: list[str] | None = None,
) -> PreprocessMetrics:
    """Create PreprocessMetrics with specified values."""
    return PreprocessMetrics(
        num_input_frames=num_input_frames,
        num_output_frames=num_output_frames,
        mask_method=mask_method,
        mask_area_ratio_mean=mask_area_ratio_mean,
        mask_area_ratio_min=mask_area_ratio_min,
        valid_frames_ratio=valid_frames_ratio,
        gate_status=gate_status,
        gate_reasons=gate_reasons or [],
    )


class TestPreprocessQualityGateInit:
    """Tests for PreprocessQualityGate initialization."""

    def test_init(self) -> None:
        """Test basic initialization."""
        gate = PreprocessQualityGate()
        assert gate._reasons == []
        assert gate._suggestions == []


class TestValidatePass:
    """Tests for validation that should PASS."""

    def test_validate_good_metrics_passes(self) -> None:
        """Test that good metrics result in PASS."""
        gate = PreprocessQualityGate()
        metrics = create_metrics()

        status = gate.validate(metrics)

        assert status == QualityStatus.PASS

    def test_validate_exactly_at_thresholds_passes(self) -> None:
        """Test metrics exactly at thresholds pass."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(
            mask_area_ratio_min=0.15,  # At warn threshold
            valid_frames_ratio=0.9,  # At warn threshold
        )

        status = gate.validate(metrics)

        assert status == QualityStatus.PASS


class TestValidateWarn:
    """Tests for validation that should WARN."""

    def test_validate_low_valid_frames_ratio_warns(self) -> None:
        """Test that low valid frames ratio results in WARN."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(valid_frames_ratio=0.85)  # Below 0.9

        status = gate.validate(metrics)

        assert status == QualityStatus.WARN
        assert len(gate._reasons) > 0

    def test_validate_low_mask_area_ratio_warns(self) -> None:
        """Test that low mask area ratio results in WARN."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(mask_area_ratio_min=0.12)  # Below 0.15 warn

        status = gate.validate(metrics)

        assert status == QualityStatus.WARN


class TestValidateFail:
    """Tests for validation that should FAIL."""

    def test_validate_no_output_frames_fails(self) -> None:
        """Test that no output frames results in FAIL."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(num_output_frames=0)

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert "no_output_frames" in gate._reasons

    def test_validate_very_low_valid_frames_ratio_fails(self) -> None:
        """Test that very low valid frames ratio results in FAIL."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(valid_frames_ratio=0.5)  # Below 0.8

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert "low_valid_frames_ratio" in gate._reasons

    def test_validate_very_low_mask_area_ratio_fails(self) -> None:
        """Test that very low mask area ratio results in FAIL."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(mask_area_ratio_min=0.05)  # Below 0.1

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert "mask_area_too_small" in gate._reasons

    def test_validate_very_high_mask_area_ratio_fails(self) -> None:
        """Test that very high mask area ratio results in FAIL."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(mask_area_ratio_mean=0.95)  # Above 0.9

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert "mask_area_too_large" in gate._reasons


class TestGetSuggestions:
    """Tests for get_suggestions method."""

    def test_get_suggestions_empty_after_pass(self) -> None:
        """Test that suggestions are empty after PASS."""
        gate = PreprocessQualityGate()
        metrics = create_metrics()

        gate.validate(metrics)
        suggestions = gate.get_suggestions()

        assert suggestions == []

    def test_get_suggestions_after_fail(self) -> None:
        """Test that suggestions exist after FAIL."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(num_output_frames=0)

        gate.validate(metrics)
        suggestions = gate.get_suggestions()

        assert len(suggestions) > 0

    def test_get_suggestions_returns_copy(self) -> None:
        """Test that get_suggestions returns a copy."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(num_output_frames=0)

        gate.validate(metrics)
        suggestions1 = gate.get_suggestions()
        suggestions2 = gate.get_suggestions()

        suggestions1.append("test")
        assert len(suggestions1) != len(suggestions2)


class TestGetReasons:
    """Tests for get_reasons method."""

    def test_get_reasons_empty_after_pass(self) -> None:
        """Test that reasons are empty after PASS."""
        gate = PreprocessQualityGate()
        metrics = create_metrics()

        gate.validate(metrics)
        reasons = gate.get_reasons()

        assert reasons == []

    def test_get_reasons_after_fail(self) -> None:
        """Test that reasons exist after FAIL."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(num_output_frames=0)

        gate.validate(metrics)
        reasons = gate.get_reasons()

        assert len(reasons) > 0

    def test_get_reasons_returns_copy(self) -> None:
        """Test that get_reasons returns a copy."""
        gate = PreprocessQualityGate()
        metrics = create_metrics(num_output_frames=0)

        gate.validate(metrics)
        reasons1 = gate.get_reasons()
        reasons2 = gate.get_reasons()

        reasons1.append("test")
        assert len(reasons1) != len(reasons2)
