"""Pipeline orchestrator.

This module provides the PipelineOrchestrator class for managing pipeline execution.
"""

import logging
from pathlib import Path

from scan2mesh.exceptions import NotImplementedStageError
from scan2mesh.models import OutputPreset, ProjectConfig
from scan2mesh.stages import ProjectInitializer


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

    def run_plan(self) -> None:
        """Run the capture planning stage.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("PipelineOrchestrator.run_plan")

    def run_capture(self) -> None:
        """Run the capture stage.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("PipelineOrchestrator.run_capture")

    def run_preprocess(self) -> None:
        """Run the preprocessing stage.

        Raises:
            NotImplementedStageError: This stage is not yet implemented
        """
        raise NotImplementedStageError("PipelineOrchestrator.run_preprocess")

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
