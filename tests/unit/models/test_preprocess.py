"""Tests for preprocess models."""

import pytest
from pydantic import ValidationError

from scan2mesh.models import MaskedFrame, MaskMethod, PreprocessMetrics


class TestMaskMethod:
    """Tests for MaskMethod enum."""

    def test_mask_method_values(self) -> None:
        """Test MaskMethod enum values."""
        assert MaskMethod.DEPTH_THRESHOLD.value == "depth_threshold"
        assert MaskMethod.FLOOR_PLANE.value == "floor_plane"
        assert MaskMethod.MANUAL_BOUNDING.value == "manual_bounding"


class TestMaskedFrame:
    """Tests for MaskedFrame model."""

    def test_masked_frame_creation(self) -> None:
        """Test MaskedFrame creation."""
        frame = MaskedFrame(
            frame_id=0,
            rgb_masked_path="masked_frames/frame_0000_rgb_masked.png",
            depth_masked_path="masked_frames/frame_0000_depth_masked.npy",
            mask_path="masked_frames/frame_0000_mask.png",
            mask_method=MaskMethod.DEPTH_THRESHOLD,
            mask_area_ratio=0.4,
            is_valid=True,
        )

        assert frame.frame_id == 0
        assert frame.mask_method == MaskMethod.DEPTH_THRESHOLD
        assert frame.mask_area_ratio == 0.4
        assert frame.is_valid is True

    def test_masked_frame_immutable(self) -> None:
        """Test MaskedFrame is immutable."""
        frame = MaskedFrame(
            frame_id=0,
            rgb_masked_path="test.png",
            depth_masked_path="test.npy",
            mask_path="mask.png",
            mask_method=MaskMethod.DEPTH_THRESHOLD,
            mask_area_ratio=0.5,
        )

        with pytest.raises(ValidationError):
            frame.frame_id = 1  # type: ignore[misc]

    def test_masked_frame_invalid_frame_id(self) -> None:
        """Test MaskedFrame rejects negative frame_id."""
        with pytest.raises(ValidationError):
            MaskedFrame(
                frame_id=-1,
                rgb_masked_path="test.png",
                depth_masked_path="test.npy",
                mask_path="mask.png",
                mask_method=MaskMethod.DEPTH_THRESHOLD,
                mask_area_ratio=0.5,
            )

    def test_masked_frame_invalid_mask_area_ratio(self) -> None:
        """Test MaskedFrame rejects invalid mask_area_ratio."""
        with pytest.raises(ValidationError):
            MaskedFrame(
                frame_id=0,
                rgb_masked_path="test.png",
                depth_masked_path="test.npy",
                mask_path="mask.png",
                mask_method=MaskMethod.DEPTH_THRESHOLD,
                mask_area_ratio=1.5,  # Above 1.0
            )


class TestPreprocessMetrics:
    """Tests for PreprocessMetrics model."""

    def test_preprocess_metrics_creation(self) -> None:
        """Test PreprocessMetrics creation."""
        metrics = PreprocessMetrics(
            num_input_frames=30,
            num_output_frames=28,
            mask_method=MaskMethod.DEPTH_THRESHOLD,
            mask_area_ratio_mean=0.4,
            mask_area_ratio_min=0.2,
            valid_frames_ratio=0.93,
            gate_status="pass",
            gate_reasons=[],
        )

        assert metrics.num_input_frames == 30
        assert metrics.num_output_frames == 28
        assert metrics.mask_method == MaskMethod.DEPTH_THRESHOLD
        assert metrics.mask_area_ratio_mean == 0.4
        assert metrics.mask_area_ratio_min == 0.2
        assert metrics.valid_frames_ratio == 0.93
        assert metrics.gate_status == "pass"
        assert metrics.gate_reasons == []

    def test_preprocess_metrics_immutable(self) -> None:
        """Test PreprocessMetrics is immutable."""
        metrics = PreprocessMetrics(
            num_input_frames=30,
            num_output_frames=28,
            mask_method=MaskMethod.DEPTH_THRESHOLD,
            mask_area_ratio_mean=0.4,
            mask_area_ratio_min=0.2,
            valid_frames_ratio=0.9,
        )

        with pytest.raises(ValidationError):
            metrics.num_input_frames = 40  # type: ignore[misc]

    def test_preprocess_metrics_invalid_num_frames(self) -> None:
        """Test PreprocessMetrics rejects negative num_frames."""
        with pytest.raises(ValidationError):
            PreprocessMetrics(
                num_input_frames=-1,
                num_output_frames=28,
                mask_method=MaskMethod.DEPTH_THRESHOLD,
                mask_area_ratio_mean=0.4,
                mask_area_ratio_min=0.2,
                valid_frames_ratio=0.9,
            )

    def test_preprocess_metrics_invalid_ratio(self) -> None:
        """Test PreprocessMetrics rejects invalid ratio."""
        with pytest.raises(ValidationError):
            PreprocessMetrics(
                num_input_frames=30,
                num_output_frames=28,
                mask_method=MaskMethod.DEPTH_THRESHOLD,
                mask_area_ratio_mean=1.5,  # Above 1.0
                mask_area_ratio_min=0.2,
                valid_frames_ratio=0.9,
            )

    def test_preprocess_metrics_default_gate_status(self) -> None:
        """Test PreprocessMetrics has default gate_status."""
        metrics = PreprocessMetrics(
            num_input_frames=30,
            num_output_frames=28,
            mask_method=MaskMethod.DEPTH_THRESHOLD,
            mask_area_ratio_mean=0.4,
            mask_area_ratio_min=0.2,
            valid_frames_ratio=0.9,
        )

        assert metrics.gate_status == "pending"
        assert metrics.gate_reasons == []

    def test_preprocess_metrics_with_gate_reasons(self) -> None:
        """Test PreprocessMetrics with gate reasons."""
        reasons = ["low_mask_area", "low_valid_frames"]
        metrics = PreprocessMetrics(
            num_input_frames=30,
            num_output_frames=28,
            mask_method=MaskMethod.DEPTH_THRESHOLD,
            mask_area_ratio_mean=0.4,
            mask_area_ratio_min=0.05,
            valid_frames_ratio=0.7,
            gate_status="fail",
            gate_reasons=reasons,
        )

        assert metrics.gate_status == "fail"
        assert metrics.gate_reasons == reasons

    def test_preprocess_metrics_serialization(self) -> None:
        """Test PreprocessMetrics serialization."""
        metrics = PreprocessMetrics(
            num_input_frames=30,
            num_output_frames=28,
            mask_method=MaskMethod.DEPTH_THRESHOLD,
            mask_area_ratio_mean=0.4,
            mask_area_ratio_min=0.2,
            valid_frames_ratio=0.9,
        )

        data = metrics.model_dump(mode="json")

        assert data["num_input_frames"] == 30
        assert data["mask_method"] == "depth_threshold"
        assert data["mask_area_ratio_mean"] == 0.4

    def test_preprocess_metrics_validation_from_dict(self) -> None:
        """Test PreprocessMetrics validation from dict."""
        data = {
            "num_input_frames": 30,
            "num_output_frames": 28,
            "mask_method": "depth_threshold",
            "mask_area_ratio_mean": 0.4,
            "mask_area_ratio_min": 0.2,
            "valid_frames_ratio": 0.9,
        }

        metrics = PreprocessMetrics.model_validate(data)

        assert metrics.num_input_frames == 30
        assert metrics.mask_method == MaskMethod.DEPTH_THRESHOLD
