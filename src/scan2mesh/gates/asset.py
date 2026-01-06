"""Asset quality gate.

This module provides the AssetQualityGate class for validating asset outputs.
"""

from scan2mesh.gates.thresholds import (
    ASSET_MAX_POLYGONS_LOD0,
    ASSET_MAX_POLYGONS_LOD1,
    ASSET_MAX_POLYGONS_LOD2,
    QualityStatus,
    QualityThresholds,
)
from scan2mesh.models import AssetMetrics


# Additional thresholds for asset validation
ASSET_MAX_HOLE_AREA_RATIO_PASS = 0.01  # 1% holes for PASS
ASSET_MAX_HOLE_AREA_RATIO_WARN = 0.05  # 5% holes for WARN
ASSET_MAX_NON_MANIFOLD_EDGES_PASS = 0  # No non-manifold edges for PASS
ASSET_MAX_NON_MANIFOLD_EDGES_WARN = 10  # Up to 10 for WARN
ASSET_MIN_LOD0_TRIANGLES = 1000  # Minimum triangles for LOD0


class AssetQualityGate:
    """Quality gate for optimized asset outputs.

    Validates:
    - Polygon count within limits for each LOD
    - Hole area ratio (mesh completeness)
    - Non-manifold edge count
    - Scale uncertainty level

    Attributes:
        thresholds: Quality threshold configuration
    """

    def __init__(self, thresholds: QualityThresholds | None = None) -> None:
        """Initialize AssetQualityGate.

        Args:
            thresholds: Quality threshold configuration (uses defaults if None)
        """
        self.thresholds = thresholds or QualityThresholds()
        self._reasons: list[str] = []
        self._suggestions: list[str] = []
        self._status: QualityStatus | None = None

    def validate(self, metrics: AssetMetrics) -> QualityStatus:
        """Validate asset outputs against quality thresholds.

        Args:
            metrics: AssetMetrics to validate

        Returns:
            QualityStatus indicating PASS, WARN, or FAIL
        """
        self._reasons = []
        self._suggestions = []

        is_fail = False
        is_warn = False

        # Check LOD triangle counts
        if metrics.lod_metrics:
            for lod in metrics.lod_metrics:
                if lod.level == 0:
                    if lod.triangles > ASSET_MAX_POLYGONS_LOD0:
                        self._reasons.append(
                            f"LOD0 has {lod.triangles} triangles, "
                            f"exceeds limit of {ASSET_MAX_POLYGONS_LOD0}"
                        )
                        is_warn = True
                    if lod.triangles < ASSET_MIN_LOD0_TRIANGLES:
                        self._reasons.append(
                            f"LOD0 has only {lod.triangles} triangles, "
                            f"minimum is {ASSET_MIN_LOD0_TRIANGLES}"
                        )
                        is_fail = True
                        self._suggestions.append(
                            "The source mesh may be too simple or reconstruction failed. "
                            "Try re-running the reconstruct stage with more frames."
                        )
                elif lod.level == 1:
                    if lod.triangles > ASSET_MAX_POLYGONS_LOD1:
                        self._reasons.append(
                            f"LOD1 has {lod.triangles} triangles, "
                            f"exceeds limit of {ASSET_MAX_POLYGONS_LOD1}"
                        )
                        is_warn = True
                elif lod.level == 2:
                    if lod.triangles > ASSET_MAX_POLYGONS_LOD2:
                        self._reasons.append(
                            f"LOD2 has {lod.triangles} triangles, "
                            f"exceeds limit of {ASSET_MAX_POLYGONS_LOD2}"
                        )
                        is_warn = True

        # Check hole area ratio
        if metrics.hole_area_ratio > ASSET_MAX_HOLE_AREA_RATIO_WARN:
            self._reasons.append(
                f"Hole area ratio is {metrics.hole_area_ratio:.1%}, "
                f"exceeds threshold of {ASSET_MAX_HOLE_AREA_RATIO_WARN:.1%}"
            )
            is_fail = True
            self._suggestions.append(
                "The mesh has significant holes. Try capturing more frames "
                "from different angles to improve coverage."
            )
        elif metrics.hole_area_ratio > ASSET_MAX_HOLE_AREA_RATIO_PASS:
            self._reasons.append(
                f"Hole area ratio is {metrics.hole_area_ratio:.1%}, "
                f"slightly above ideal threshold of {ASSET_MAX_HOLE_AREA_RATIO_PASS:.1%}"
            )
            is_warn = True
            self._suggestions.append(
                "The mesh has minor holes which may be acceptable for most use cases."
            )

        # Check non-manifold edges
        if metrics.non_manifold_edges > ASSET_MAX_NON_MANIFOLD_EDGES_WARN:
            self._reasons.append(
                f"Non-manifold edges: {metrics.non_manifold_edges}, "
                f"exceeds threshold of {ASSET_MAX_NON_MANIFOLD_EDGES_WARN}"
            )
            is_fail = True
            self._suggestions.append(
                "The mesh has significant non-manifold geometry. "
                "This may cause issues with simulation or rendering."
            )
        elif metrics.non_manifold_edges > ASSET_MAX_NON_MANIFOLD_EDGES_PASS:
            self._reasons.append(
                f"Non-manifold edges: {metrics.non_manifold_edges}, "
                f"ideally should be {ASSET_MAX_NON_MANIFOLD_EDGES_PASS}"
            )
            is_warn = True

        # Check scale uncertainty
        if metrics.scale_uncertainty == "high":
            self._reasons.append("Scale uncertainty is high")
            is_warn = True
            self._suggestions.append(
                "Consider providing a known dimension for more accurate scale. "
                "Use --dimension and --dimension-type options when initializing the project."
            )

        # Determine final status
        if is_fail:
            self._status = QualityStatus.FAIL
        elif is_warn:
            self._status = QualityStatus.WARN
        else:
            self._status = QualityStatus.PASS

        return self._status

    def get_suggestions(self) -> list[str]:
        """Get improvement suggestions based on validation results.

        Returns:
            List of suggestions for improving asset quality
        """
        return self._suggestions.copy()

    def get_reasons(self) -> list[str]:
        """Get reasons for the quality status.

        Returns:
            List of reasons explaining the quality status
        """
        return self._reasons.copy()

    def get_report(self) -> dict[str, object]:
        """Generate detailed validation report.

        Returns:
            Dictionary containing validation details
        """
        return {
            "status": self._status.value if self._status else "pending",
            "reasons": self._reasons,
            "suggestions": self._suggestions,
        }
