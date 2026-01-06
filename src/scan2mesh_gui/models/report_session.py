"""Report session models for quality report generation and export."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from scan2mesh_gui.models.scan_object import QualityStatus


class ActionPriority(str, Enum):
    """Priority level for recommended actions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QualityGateResult(BaseModel):
    """Result of a single quality gate evaluation."""

    gate_name: str = Field(..., description="Name of the quality gate")
    status: QualityStatus = Field(..., description="Gate evaluation status")
    value: float | int | str = Field(..., description="Actual metric value")
    threshold: str = Field(..., description="Threshold description")
    reason: str = Field(..., description="Reason for the status")


class RecommendedAction(BaseModel):
    """A recommended action to improve quality."""

    action: str = Field(..., description="Description of the recommended action")
    priority: ActionPriority = Field(..., description="Priority level")
    target_stage: str = Field(..., description="Pipeline stage to address")


class CaptureMetricsSummary(BaseModel):
    """Summary of capture metrics for the report."""

    num_keyframes: int = Field(default=0, ge=0, description="Number of keyframes")
    depth_valid_ratio: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean depth valid ratio"
    )
    blur_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean blur score"
    )
    coverage: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Coverage score"
    )


class PreprocessMetricsSummary(BaseModel):
    """Summary of preprocess metrics for the report."""

    num_frames_processed: int = Field(
        default=0, ge=0, description="Number of frames processed"
    )
    num_valid_masks: int = Field(
        default=0, ge=0, description="Number of valid masks"
    )
    mask_area_ratio_mean: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean mask area ratio"
    )
    edge_quality_mean: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean edge quality"
    )


class ReconstructMetricsSummary(BaseModel):
    """Summary of reconstruction metrics for the report."""

    num_vertices: int = Field(default=0, ge=0, description="Number of mesh vertices")
    num_triangles: int = Field(default=0, ge=0, description="Number of mesh triangles")
    is_watertight: bool = Field(default=False, description="Whether mesh is watertight")
    num_holes: int = Field(default=0, ge=0, description="Number of holes in mesh")
    surface_coverage: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Surface coverage ratio"
    )
    keyframes_used: int = Field(default=0, ge=0, description="Number of keyframes used")
    tracking_loss_frames: int = Field(
        default=0, ge=0, description="Number of frames with tracking loss"
    )
    texture_resolution: tuple[int, int] = Field(
        default=(0, 0), description="Texture resolution (width, height)"
    )


class OptimizeMetricsSummary(BaseModel):
    """Summary of optimization metrics for the report."""

    scale_factor: float = Field(default=1.0, ge=0.0, description="Applied scale factor")
    holes_filled: int = Field(default=0, ge=0, description="Number of holes filled")
    components_removed: int = Field(
        default=0, ge=0, description="Number of isolated components removed"
    )
    lod0_triangles: int = Field(default=0, ge=0, description="LOD0 triangle count")
    lod1_triangles: int = Field(default=0, ge=0, description="LOD1 triangle count")
    lod2_triangles: int = Field(default=0, ge=0, description="LOD2 triangle count")
    collision_triangles: int = Field(
        default=0, ge=0, description="Collision mesh triangle count"
    )
    texture_resolution: tuple[int, int] = Field(
        default=(0, 0), description="Final texture resolution"
    )
    bounding_box: tuple[float, float, float] = Field(
        default=(0.0, 0.0, 0.0), description="Bounding box dimensions (meters)"
    )


class PackageMetricsSummary(BaseModel):
    """Summary of packaging metrics for the report."""

    files_count: int = Field(default=0, ge=0, description="Number of files included")
    total_size_mb: float = Field(
        default=0.0, ge=0.0, description="Total size in megabytes"
    )
    compressed_size_mb: float | None = Field(
        default=None, description="Compressed size in megabytes (ZIP only)"
    )
    output_path: str = Field(default="", description="Output file/directory path")


class ReportSession(BaseModel):
    """A report session containing all metrics and quality evaluation."""

    session_id: str = Field(..., description="Unique session identifier")
    object_id: str = Field(..., description="ID of the scanned object")
    object_name: str = Field(..., description="Name of the scanned object")
    display_name: str = Field(..., description="Display name of the object")

    # Overall status
    overall_status: QualityStatus = Field(
        default=QualityStatus.PENDING, description="Overall quality status"
    )
    status_message: str = Field(
        default="Quality evaluation pending", description="Status description"
    )

    # Metrics summaries
    capture_metrics: CaptureMetricsSummary | None = Field(
        default=None, description="Capture metrics summary"
    )
    preprocess_metrics: PreprocessMetricsSummary | None = Field(
        default=None, description="Preprocess metrics summary"
    )
    reconstruct_metrics: ReconstructMetricsSummary | None = Field(
        default=None, description="Reconstruction metrics summary"
    )
    optimize_metrics: OptimizeMetricsSummary | None = Field(
        default=None, description="Optimization metrics summary"
    )
    package_metrics: PackageMetricsSummary | None = Field(
        default=None, description="Package metrics summary"
    )

    # Quality gates and recommendations
    quality_gates: list[QualityGateResult] = Field(
        default_factory=list, description="Results of quality gate evaluations"
    )
    recommendations: list[RecommendedAction] = Field(
        default_factory=list, description="Recommended actions for improvement"
    )

    # Timestamps
    generated_at: datetime = Field(
        default_factory=datetime.now, description="When the report was generated"
    )

    def to_markdown(self) -> str:
        """Generate a Markdown report.

        Returns:
            Markdown-formatted report string.
        """
        lines = [
            f"# Quality Report: {self.display_name}",
            "",
            f"**Object Name:** {self.object_name}",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            f"## Overall Status: {self.overall_status.value.upper()}",
            "",
            f"{self.status_message}",
            "",
        ]

        # Capture Metrics
        if self.capture_metrics:
            lines.extend([
                "## Capture Metrics",
                "",
                f"- **Keyframes:** {self.capture_metrics.num_keyframes}",
                f"- **Depth Valid Ratio:** {self.capture_metrics.depth_valid_ratio:.2f}",
                f"- **Blur Score:** {self.capture_metrics.blur_score:.2f}",
                f"- **Coverage:** {self.capture_metrics.coverage:.2f}",
                "",
            ])

        # Preprocess Metrics
        if self.preprocess_metrics:
            lines.extend([
                "## Preprocess Metrics",
                "",
                f"- **Frames Processed:** {self.preprocess_metrics.num_frames_processed}",
                f"- **Valid Masks:** {self.preprocess_metrics.num_valid_masks}",
                f"- **Mask Area Ratio:** {self.preprocess_metrics.mask_area_ratio_mean:.2f}",
                f"- **Edge Quality:** {self.preprocess_metrics.edge_quality_mean:.2f}",
                "",
            ])

        # Reconstruction Metrics
        if self.reconstruct_metrics:
            lines.extend([
                "## Reconstruction Metrics",
                "",
                f"- **Vertices:** {self.reconstruct_metrics.num_vertices:,}",
                f"- **Triangles:** {self.reconstruct_metrics.num_triangles:,}",
                f"- **Watertight:** {'Yes' if self.reconstruct_metrics.is_watertight else 'No'}",
                f"- **Holes:** {self.reconstruct_metrics.num_holes}",
                f"- **Surface Coverage:** {self.reconstruct_metrics.surface_coverage:.2f}",
                f"- **Keyframes Used:** {self.reconstruct_metrics.keyframes_used}",
                f"- **Tracking Loss Frames:** {self.reconstruct_metrics.tracking_loss_frames}",
                f"- **Texture Resolution:** {self.reconstruct_metrics.texture_resolution[0]}x{self.reconstruct_metrics.texture_resolution[1]}",
                "",
            ])

        # Optimization Metrics
        if self.optimize_metrics:
            lines.extend([
                "## Optimization Metrics",
                "",
                f"- **Scale Factor:** {self.optimize_metrics.scale_factor:.4f}",
                f"- **Holes Filled:** {self.optimize_metrics.holes_filled}",
                f"- **Components Removed:** {self.optimize_metrics.components_removed}",
                f"- **LOD0 Triangles:** {self.optimize_metrics.lod0_triangles:,}",
                f"- **LOD1 Triangles:** {self.optimize_metrics.lod1_triangles:,}",
                f"- **LOD2 Triangles:** {self.optimize_metrics.lod2_triangles:,}",
                f"- **Collision Triangles:** {self.optimize_metrics.collision_triangles:,}",
                f"- **Texture Resolution:** {self.optimize_metrics.texture_resolution[0]}x{self.optimize_metrics.texture_resolution[1]}",
                f"- **Bounding Box:** {self.optimize_metrics.bounding_box[0]:.3f}m x {self.optimize_metrics.bounding_box[1]:.3f}m x {self.optimize_metrics.bounding_box[2]:.3f}m",
                "",
            ])

        # Package Metrics
        if self.package_metrics:
            lines.extend([
                "## Package Metrics",
                "",
                f"- **Files Count:** {self.package_metrics.files_count}",
                f"- **Total Size:** {self.package_metrics.total_size_mb:.1f} MB",
            ])
            if self.package_metrics.compressed_size_mb is not None:
                lines.append(
                    f"- **Compressed Size:** {self.package_metrics.compressed_size_mb:.1f} MB"
                )
            lines.extend([
                f"- **Output Path:** `{self.package_metrics.output_path}`",
                "",
            ])

        # Quality Gates
        if self.quality_gates:
            lines.extend([
                "## Quality Gate Results",
                "",
                "| Gate | Status | Value | Threshold | Reason |",
                "|------|--------|-------|-----------|--------|",
            ])
            for gate in self.quality_gates:
                status_emoji = (
                    "PASS" if gate.status == QualityStatus.PASS
                    else "WARN" if gate.status == QualityStatus.WARN
                    else "FAIL" if gate.status == QualityStatus.FAIL
                    else "PENDING"
                )
                lines.append(
                    f"| {gate.gate_name} | {status_emoji} | {gate.value} | {gate.threshold} | {gate.reason} |"
                )
            lines.append("")

        # Recommendations
        if self.recommendations:
            lines.extend([
                "## Recommended Actions",
                "",
            ])
            for rec in self.recommendations:
                priority_marker = (
                    "[HIGH]" if rec.priority == ActionPriority.HIGH
                    else "[MEDIUM]" if rec.priority == ActionPriority.MEDIUM
                    else "[LOW]"
                )
                lines.append(f"- {priority_marker} **{rec.target_stage}**: {rec.action}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "*Generated by scan2mesh GUI*",
        ])

        return "\n".join(lines)

    def to_json_dict(self) -> dict[str, Any]:
        """Generate a JSON-serializable dictionary.

        Returns:
            Dictionary suitable for JSON serialization.
        """
        result: dict[str, Any] = {
            "session_id": self.session_id,
            "object_id": self.object_id,
            "object_name": self.object_name,
            "display_name": self.display_name,
            "overall_status": self.overall_status.value,
            "status_message": self.status_message,
            "generated_at": self.generated_at.isoformat(),
        }

        if self.capture_metrics:
            result["capture_metrics"] = self.capture_metrics.model_dump()

        if self.preprocess_metrics:
            result["preprocess_metrics"] = self.preprocess_metrics.model_dump()

        if self.reconstruct_metrics:
            result["reconstruct_metrics"] = self.reconstruct_metrics.model_dump()

        if self.optimize_metrics:
            result["optimize_metrics"] = self.optimize_metrics.model_dump()

        if self.package_metrics:
            result["package_metrics"] = self.package_metrics.model_dump()

        result["quality_gates"] = [
            {
                "gate_name": g.gate_name,
                "status": g.status.value,
                "value": g.value,
                "threshold": g.threshold,
                "reason": g.reason,
            }
            for g in self.quality_gates
        ]

        result["recommendations"] = [
            {
                "action": r.action,
                "priority": r.priority.value,
                "target_stage": r.target_stage,
            }
            for r in self.recommendations
        ]

        return result
