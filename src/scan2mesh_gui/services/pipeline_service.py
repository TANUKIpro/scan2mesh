"""Pipeline execution service wrapping scan2mesh Core."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from scan2mesh_gui.models.scan_object import PipelineStage, QualityStatus, ScanObject


class PipelineService:
    """Service for executing scan2mesh pipeline stages."""

    def __init__(self, projects_dir: Path) -> None:
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def init_project(self, obj: ScanObject) -> Path:
        """Initialize a scan2mesh project for an object."""
        project_path = self.projects_dir / obj.id
        project_path.mkdir(parents=True, exist_ok=True)

        # Create standard directories
        (project_path / "raw_frames").mkdir(exist_ok=True)
        (project_path / "masked_frames").mkdir(exist_ok=True)
        (project_path / "recon").mkdir(exist_ok=True)
        (project_path / "asset").mkdir(exist_ok=True)
        (project_path / "metrics").mkdir(exist_ok=True)

        return project_path

    def generate_plan(
        self,
        project_path: Path,
        preset: str = "standard",
    ) -> dict[str, Any]:
        """Generate a capture plan."""
        # TODO: Call scan2mesh Core CapturePlanner
        viewpoint_counts = {"quick": 16, "standard": 24, "hard": 48}
        return {
            "preset": preset,
            "viewpoints": viewpoint_counts.get(preset, 24),
            "recommended_distance_m": 0.3,
        }

    def start_capture(
        self,
        project_path: Path,
        on_frame: Callable[[dict[str, Any]], None] | None = None,
        on_quality: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """Start capture (called in a separate thread)."""
        # TODO: Implement with scan2mesh Core RGBDCapture
        pass

    def stop_capture(self, project_path: Path) -> dict[str, Any]:
        """Stop capture and return metrics."""
        # TODO: Implement with scan2mesh Core
        return {
            "num_frames_raw": 0,
            "num_keyframes": 0,
            "gate_status": "pending",
        }

    def run_preprocess(
        self,
        project_path: Path,
        method: str,
        on_progress: Callable[[float], None] | None = None,
    ) -> dict[str, Any]:
        """Run preprocessing."""
        # TODO: Implement with scan2mesh Core Preprocessor
        return {"method": method, "processed_frames": 0}

    def run_reconstruct(
        self,
        project_path: Path,
        on_progress: Callable[[float, str], None] | None = None,
    ) -> dict[str, Any]:
        """Run 3D reconstruction."""
        # TODO: Implement with scan2mesh Core Reconstructor
        return {
            "mesh_vertices": 0,
            "mesh_triangles": 0,
            "gate_status": "pending",
        }

    def run_optimize(
        self,
        project_path: Path,
        options: dict[str, Any],
        on_progress: Callable[[float], None] | None = None,
    ) -> dict[str, Any]:
        """Run asset optimization."""
        # TODO: Implement with scan2mesh Core AssetOptimizer
        return {"lod_levels": 3, "gate_status": "pending"}

    def run_package(
        self,
        project_path: Path,
        output_path: Path,
        as_zip: bool = False,
    ) -> Path:
        """Run packaging."""
        # TODO: Implement with scan2mesh Core Packager
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path

    def get_metrics(self, project_path: Path) -> dict[str, Any]:
        """Get all metrics for a project."""
        # TODO: Load from metrics directory
        return {
            "capture": {},
            "preprocess": {},
            "reconstruct": {},
            "asset": {},
        }

    def get_quality_status(
        self, project_path: Path
    ) -> tuple[QualityStatus, list[str]]:
        """Get overall quality status and reasons."""
        # TODO: Evaluate with scan2mesh Core quality gates
        return QualityStatus.PENDING, []

    def get_current_stage(self, project_path: Path) -> PipelineStage:
        """Determine the current pipeline stage based on project state."""
        if not project_path.exists():
            return PipelineStage.INIT

        # Check for stage markers
        if (project_path / "asset" / "visual_lod0.glb").exists():
            return PipelineStage.PACKAGE
        if (project_path / "recon" / "mesh_raw.glb").exists():
            return PipelineStage.OPTIMIZE
        if (project_path / "masked_frames").exists() and any(
            (project_path / "masked_frames").iterdir()
        ):
            return PipelineStage.RECONSTRUCT
        if (project_path / "raw_frames").exists() and any(
            (project_path / "raw_frames").iterdir()
        ):
            return PipelineStage.PREPROCESS
        if (project_path / "capture_plan.json").exists():
            return PipelineStage.CAPTURE

        return PipelineStage.PLAN
