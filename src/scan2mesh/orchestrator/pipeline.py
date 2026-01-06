"""Pipeline orchestrator.

This module provides the PipelineOrchestrator class for managing pipeline execution.
"""

import logging
from pathlib import Path

from scan2mesh.exceptions import NotImplementedStageError
from scan2mesh.gates.capture import CaptureQualityGate
from scan2mesh.gates.preprocess import PreprocessQualityGate
from scan2mesh.gates.thresholds import QualityStatus
from scan2mesh.models import (
    CaptureMetrics,
    CapturePlan,
    CapturePlanPreset,
    MaskMethod,
    OutputPreset,
    PreprocessMetrics,
    ProjectConfig,
)
from scan2mesh.services import BaseCameraService, StorageService, create_camera_service
from scan2mesh.stages import (
    CapturePlanner,
    Preprocessor,
    ProjectInitializer,
    RGBDCapture,
)


logger = logging.getLogger("scan2mesh.orchestrator.pipeline")


class PipelineOrchestrator:
    """Orchestrate the scan2mesh pipeline execution.

    Manages the execution of all pipeline stages in sequence,
    handling errors, recovery, and progress tracking.

    Attributes:
        project_dir: Path to the project directory
    """

    def __init__(self, project_dir: Path) -> None:
        """Initialize PipelineOrchestrator.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir

    def run_init(
        self,
        object_name: str,
        class_id: int,
        preset: OutputPreset | None = None,
        tags: list[str] | None = None,
        known_dimension_mm: float | None = None,
        dimension_type: str | None = None,
    ) -> ProjectConfig:
        """Run the initialization stage.

        Creates a new project with the specified parameters.

        Args:
            object_name: Name of the object to scan
            class_id: Class ID for the object (0-9999)
            preset: Output preset configuration (optional)
            tags: List of tags for categorization (optional)
            known_dimension_mm: Known dimension in millimeters (optional)
            dimension_type: Type of known dimension (optional)

        Returns:
            ProjectConfig instance with the created configuration
        """
        logger.info(f"Running init stage for project: {self.project_dir}")
        initializer = ProjectInitializer(self.project_dir)
        return initializer.initialize(
            object_name=object_name,
            class_id=class_id,
            preset=preset,
            tags=tags,
            known_dimension_mm=known_dimension_mm,
            dimension_type=dimension_type,
        )

    def run_plan(
        self, preset: CapturePlanPreset = CapturePlanPreset.STANDARD
    ) -> CapturePlan:
        """Run the capture planning stage.

        Creates a capture plan based on the given preset.

        Args:
            preset: Capture plan preset type (default: STANDARD)

        Returns:
            CapturePlan instance
        """
        logger.info(f"Running plan stage for project: {self.project_dir}")
        planner = CapturePlanner(self.project_dir)
        return planner.generate_plan(preset)

    def run_capture(
        self,
        num_frames: int = 30,
        use_mock: bool = False,
        camera: BaseCameraService | None = None,
    ) -> tuple[CaptureMetrics, QualityStatus, list[str]]:
        """Run the capture stage.

        Args:
            num_frames: Number of frames to capture
            use_mock: If True, use mock camera for testing
            camera: Optional pre-configured camera service

        Returns:
            Tuple of (CaptureMetrics, QualityStatus, suggestions)
        """
        logger.info(f"Running capture stage for project: {self.project_dir}")

        # Load capture plan if available
        storage = StorageService(self.project_dir)
        try:
            capture_plan = storage.load_capture_plan()
        except Exception:
            capture_plan = None

        # Create camera service if not provided
        if camera is None:
            camera = create_camera_service(use_mock=use_mock)

        # Create and run capture stage
        capture_stage = RGBDCapture(
            project_dir=self.project_dir,
            camera=camera,
            storage=storage,
        )

        capture_stage.start_capture(plan=capture_plan)

        try:
            # Capture frames
            for _ in range(num_frames):
                capture_stage.capture_frame()

            # Stop capture and get metrics
            metrics = capture_stage.stop_capture()
        except Exception:
            # Ensure we stop capturing on error
            import contextlib

            with contextlib.suppress(Exception):
                capture_stage.stop_capture()
            raise

        # Run quality gate
        gate = CaptureQualityGate()
        status = gate.validate(metrics)
        suggestions = gate.get_suggestions()

        # Update metrics with gate status
        metrics_with_status = CaptureMetrics(
            num_frames_raw=metrics.num_frames_raw,
            num_keyframes=metrics.num_keyframes,
            depth_valid_ratio_mean=metrics.depth_valid_ratio_mean,
            depth_valid_ratio_min=metrics.depth_valid_ratio_min,
            blur_score_mean=metrics.blur_score_mean,
            blur_score_min=metrics.blur_score_min,
            coverage_score=metrics.coverage_score,
            capture_duration_sec=metrics.capture_duration_sec,
            gate_status=status.value,
            gate_reasons=gate._reasons,
        )

        # Save updated metrics
        storage.save_capture_metrics(metrics_with_status)

        return metrics_with_status, status, suggestions

    def run_preprocess(
        self,
        mask_method: MaskMethod = MaskMethod.DEPTH_THRESHOLD,
        depth_min_mm: int = 200,
        depth_max_mm: int = 1000,
    ) -> tuple[PreprocessMetrics, QualityStatus, list[str]]:
        """Run the preprocessing stage.

        Args:
            mask_method: Method to use for background removal
            depth_min_mm: Minimum depth threshold in mm
            depth_max_mm: Maximum depth threshold in mm

        Returns:
            Tuple of (PreprocessMetrics, QualityStatus, suggestions)
        """
        logger.info(f"Running preprocess stage for project: {self.project_dir}")

        storage = StorageService(self.project_dir)

        # Create and run preprocessor
        preprocessor = Preprocessor(
            project_dir=self.project_dir,
            storage=storage,
            depth_min_mm=depth_min_mm,
            depth_max_mm=depth_max_mm,
        )

        metrics = preprocessor.preprocess(mask_method=mask_method)

        # Run quality gate
        gate = PreprocessQualityGate()
        status = gate.validate(metrics)
        suggestions = gate.get_suggestions()

        # Update metrics with gate status
        metrics_with_status = PreprocessMetrics(
            num_input_frames=metrics.num_input_frames,
            num_output_frames=metrics.num_output_frames,
            mask_method=metrics.mask_method,
            mask_area_ratio_mean=metrics.mask_area_ratio_mean,
            mask_area_ratio_min=metrics.mask_area_ratio_min,
            valid_frames_ratio=metrics.valid_frames_ratio,
            gate_status=status.value,
            gate_reasons=gate.get_reasons(),
        )

        # Save updated metrics
        storage.save_preprocess_metrics(metrics_with_status)

        return metrics_with_status, status, suggestions

    def run_reconstruct(self) -> None:
        """Run the reconstruction stage.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("PipelineOrchestrator.run_reconstruct")

    def run_optimize(self) -> None:
        """Run the optimization stage.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("PipelineOrchestrator.run_optimize")

    def run_package(self) -> None:
        """Run the packaging stage.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("PipelineOrchestrator.run_package")

    def run_report(self) -> None:
        """Run the reporting stage.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("PipelineOrchestrator.run_report")

    def run_full_pipeline(self) -> None:
        """Run the complete pipeline from start to finish.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("PipelineOrchestrator.run_full_pipeline")
