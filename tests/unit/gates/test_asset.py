"""Tests for AssetQualityGate."""

from scan2mesh.gates.asset import (
    ASSET_MAX_HOLE_AREA_RATIO_PASS,
    ASSET_MAX_HOLE_AREA_RATIO_WARN,
    ASSET_MAX_NON_MANIFOLD_EDGES_PASS,
    ASSET_MAX_NON_MANIFOLD_EDGES_WARN,
    ASSET_MIN_LOD0_TRIANGLES,
    AssetQualityGate,
)
from scan2mesh.gates.thresholds import (
    ASSET_MAX_POLYGONS_LOD0,
    QualityStatus,
)
from scan2mesh.models import AssetMetrics, CollisionMetrics, LODMetrics


def create_metrics(
    lod0_triangles: int = 50000,
    lod1_triangles: int = 20000,
    lod2_triangles: int = 5000,
    hole_area_ratio: float = 0.0,
    non_manifold_edges: int = 0,
    scale_uncertainty: str = "low",
    gate_status: str = "pending",
    gate_reasons: list[str] | None = None,
) -> AssetMetrics:
    """Create AssetMetrics with specified values."""
    lod_metrics = [
        LODMetrics(level=0, triangles=lod0_triangles, vertices=lod0_triangles // 2, file_size_bytes=1000000),
        LODMetrics(level=1, triangles=lod1_triangles, vertices=lod1_triangles // 2, file_size_bytes=500000),
        LODMetrics(level=2, triangles=lod2_triangles, vertices=lod2_triangles // 2, file_size_bytes=100000),
    ]
    collision_metrics = CollisionMetrics(
        method="convex_hull",
        num_convex_parts=1,
        total_triangles=100,
    )
    return AssetMetrics(
        lod_metrics=lod_metrics,
        collision_metrics=collision_metrics,
        aabb_size=[0.1, 0.1, 0.1],
        obb_size=[0.1, 0.1, 0.1],
        hole_area_ratio=hole_area_ratio,
        non_manifold_edges=non_manifold_edges,
        texture_resolution=2048,
        texture_coverage=0.0,
        scale_uncertainty=scale_uncertainty,
        gate_status=gate_status,
        gate_reasons=gate_reasons or [],
    )


class TestAssetQualityGateInit:
    """Tests for AssetQualityGate initialization."""

    def test_init(self) -> None:
        """Test basic initialization."""
        gate = AssetQualityGate()
        assert gate._reasons == []
        assert gate._suggestions == []


class TestValidatePass:
    """Tests for validation that should PASS."""

    def test_validate_good_metrics_passes(self) -> None:
        """Test that good metrics result in PASS."""
        gate = AssetQualityGate()
        metrics = create_metrics()

        status = gate.validate(metrics)

        assert status == QualityStatus.PASS

    def test_validate_at_ideal_thresholds_passes(self) -> None:
        """Test metrics at ideal thresholds."""
        gate = AssetQualityGate()
        metrics = create_metrics(
            hole_area_ratio=0.0,
            non_manifold_edges=0,
            scale_uncertainty="low",
        )

        status = gate.validate(metrics)

        assert status == QualityStatus.PASS


class TestValidateWarn:
    """Tests for validation that should WARN."""

    def test_validate_high_scale_uncertainty_warns(self) -> None:
        """Test that high scale uncertainty results in WARN."""
        gate = AssetQualityGate()
        metrics = create_metrics(scale_uncertainty="high")

        status = gate.validate(metrics)

        assert status == QualityStatus.WARN
        assert len(gate._reasons) > 0

    def test_validate_minor_hole_area_warns(self) -> None:
        """Test that minor hole area ratio results in WARN."""
        gate = AssetQualityGate()
        metrics = create_metrics(
            hole_area_ratio=(ASSET_MAX_HOLE_AREA_RATIO_PASS + ASSET_MAX_HOLE_AREA_RATIO_WARN) / 2
        )

        status = gate.validate(metrics)

        assert status == QualityStatus.WARN

    def test_validate_minor_non_manifold_edges_warns(self) -> None:
        """Test that minor non-manifold edges result in WARN."""
        gate = AssetQualityGate()
        metrics = create_metrics(
            non_manifold_edges=(ASSET_MAX_NON_MANIFOLD_EDGES_PASS + ASSET_MAX_NON_MANIFOLD_EDGES_WARN) // 2 + 1
        )

        status = gate.validate(metrics)

        assert status == QualityStatus.WARN

    def test_validate_lod0_over_limit_warns(self) -> None:
        """Test that LOD0 over polygon limit results in WARN."""
        gate = AssetQualityGate()
        metrics = create_metrics(lod0_triangles=ASSET_MAX_POLYGONS_LOD0 + 1000)

        status = gate.validate(metrics)

        assert status == QualityStatus.WARN


class TestValidateFail:
    """Tests for validation that should FAIL."""

    def test_validate_low_lod0_triangles_fails(self) -> None:
        """Test that low LOD0 triangles results in FAIL."""
        gate = AssetQualityGate()
        metrics = create_metrics(lod0_triangles=ASSET_MIN_LOD0_TRIANGLES - 1)

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert len(gate._suggestions) > 0

    def test_validate_high_hole_area_fails(self) -> None:
        """Test that high hole area ratio results in FAIL."""
        gate = AssetQualityGate()
        metrics = create_metrics(hole_area_ratio=ASSET_MAX_HOLE_AREA_RATIO_WARN + 0.01)

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL

    def test_validate_high_non_manifold_edges_fails(self) -> None:
        """Test that high non-manifold edge count results in FAIL."""
        gate = AssetQualityGate()
        metrics = create_metrics(non_manifold_edges=ASSET_MAX_NON_MANIFOLD_EDGES_WARN + 1)

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL

    def test_validate_multiple_issues_fails(self) -> None:
        """Test that multiple issues result in FAIL with all reasons."""
        gate = AssetQualityGate()
        metrics = create_metrics(
            lod0_triangles=500,  # FAIL
            hole_area_ratio=0.1,  # FAIL
            non_manifold_edges=20,  # FAIL
        )

        status = gate.validate(metrics)

        assert status == QualityStatus.FAIL
        assert len(gate._reasons) >= 3


class TestGetSuggestions:
    """Tests for get_suggestions method."""

    def test_get_suggestions_empty_after_pass(self) -> None:
        """Test that suggestions are empty after PASS."""
        gate = AssetQualityGate()
        metrics = create_metrics()

        gate.validate(metrics)
        suggestions = gate.get_suggestions()

        assert suggestions == []

    def test_get_suggestions_after_fail(self) -> None:
        """Test that suggestions exist after FAIL."""
        gate = AssetQualityGate()
        metrics = create_metrics(lod0_triangles=500)

        gate.validate(metrics)
        suggestions = gate.get_suggestions()

        assert len(suggestions) > 0

    def test_get_suggestions_returns_copy(self) -> None:
        """Test that get_suggestions returns a copy."""
        gate = AssetQualityGate()
        metrics = create_metrics(lod0_triangles=500)

        gate.validate(metrics)
        suggestions1 = gate.get_suggestions()
        suggestions2 = gate.get_suggestions()

        suggestions1.append("test")
        assert len(suggestions1) != len(suggestions2)


class TestGetReasons:
    """Tests for get_reasons method."""

    def test_get_reasons_empty_after_pass(self) -> None:
        """Test that reasons are empty after PASS."""
        gate = AssetQualityGate()
        metrics = create_metrics()

        gate.validate(metrics)
        reasons = gate.get_reasons()

        assert reasons == []

    def test_get_reasons_after_fail(self) -> None:
        """Test that reasons exist after FAIL."""
        gate = AssetQualityGate()
        metrics = create_metrics(lod0_triangles=500)

        gate.validate(metrics)
        reasons = gate.get_reasons()

        assert len(reasons) > 0

    def test_get_reasons_returns_copy(self) -> None:
        """Test that get_reasons returns a copy."""
        gate = AssetQualityGate()
        metrics = create_metrics(lod0_triangles=500)

        gate.validate(metrics)
        reasons1 = gate.get_reasons()
        reasons2 = gate.get_reasons()

        reasons1.append("test")
        assert len(reasons1) != len(reasons2)


class TestGetReport:
    """Tests for get_report method."""

    def test_get_report_structure(self) -> None:
        """Test that get_report returns expected structure."""
        gate = AssetQualityGate()
        metrics = create_metrics(scale_uncertainty="high")

        gate.validate(metrics)
        report = gate.get_report()

        assert "status" in report
        assert "reasons" in report
        assert "suggestions" in report
