"""Capture planning stage.

This module provides the CapturePlanner class for generating optimal capture plans.
"""

import logging
from pathlib import Path
from typing import Any, ClassVar

from scan2mesh.exceptions import ConfigError
from scan2mesh.models import CapturePlan, CapturePlanPreset, ViewPoint
from scan2mesh.services import StorageService


logger = logging.getLogger("scan2mesh.stages.plan")


class CapturePlanner:
    """Plan optimal camera viewpoints for 3D reconstruction.

    This stage handles:
    - Generating viewpoint trajectories based on presets
    - Optimizing coverage for reconstruction quality
    - Saving and loading capture plans

    Attributes:
        project_dir: Path to the project directory
        storage: StorageService instance
    """

    QUICK_CONFIG: ClassVar[dict[str, Any]] = {
        "num_azimuths": 8,
        "elevations": [0.0, 30.0],
        "min_required_frames": 12,
        "recommended_distance_m": 0.4,
    }

    STANDARD_CONFIG: ClassVar[dict[str, Any]] = {
        "num_azimuths": 12,
        "elevations": [-15.0, 15.0, 45.0],
        "min_required_frames": 20,
        "recommended_distance_m": 0.4,
    }

    HARD_CONFIG: ClassVar[dict[str, Any]] = {
        "num_azimuths": 12,
        "elevations": [-30.0, 0.0, 30.0, 60.0],
        "min_required_frames": 30,
        "recommended_distance_m": 0.35,
    }

    def __init__(self, project_dir: Path) -> None:
        """Initialize CapturePlanner.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir
        self.storage = StorageService(project_dir)

    def _get_config(self, preset: CapturePlanPreset) -> dict[str, Any]:
        """Get configuration for the given preset.

        Args:
            preset: Capture plan preset type

        Returns:
            Configuration dictionary for the preset
        """
        configs = {
            CapturePlanPreset.QUICK: self.QUICK_CONFIG,
            CapturePlanPreset.STANDARD: self.STANDARD_CONFIG,
            CapturePlanPreset.HARD: self.HARD_CONFIG,
        }
        return configs[preset]

    def get_viewpoints(self, preset: CapturePlanPreset) -> list[ViewPoint]:
        """Generate viewpoint list for the given preset.

        Creates a list of viewpoints with evenly distributed azimuths
        and preset-specific elevation angles.

        Args:
            preset: Capture plan preset type

        Returns:
            List of ViewPoint objects
        """
        config = self._get_config(preset)
        num_azimuths: int = config["num_azimuths"]
        elevations: list[float] = config["elevations"]
        distance_m: float = config["recommended_distance_m"]

        viewpoints: list[ViewPoint] = []
        index = 0

        for elevation in elevations:
            for i in range(num_azimuths):
                azimuth = (360.0 / num_azimuths) * i
                viewpoint = ViewPoint(
                    index=index,
                    azimuth_deg=azimuth,
                    elevation_deg=elevation,
                    distance_m=distance_m,
                    order=index,
                )
                viewpoints.append(viewpoint)
                index += 1

        logger.debug(
            f"Generated {len(viewpoints)} viewpoints for preset {preset.value}"
        )
        return viewpoints

    def generate_plan(self, preset: CapturePlanPreset) -> CapturePlan:
        """Generate a capture plan for the project.

        Creates a capture plan based on the given preset and saves it
        to the project directory.

        Args:
            preset: Capture plan preset type

        Returns:
            CapturePlan instance

        Raises:
            ConfigError: If the project is not initialized
        """
        logger.info(f"Generating capture plan with preset: {preset.value}")

        if not self.storage.project_exists():
            raise ConfigError(
                f"Project not initialized: {self.project_dir}. "
                "Run 'scan2mesh init' first."
            )

        config = self._get_config(preset)
        viewpoints = self.get_viewpoints(preset)

        notes = self._generate_notes(preset)

        plan = CapturePlan(
            preset=preset,
            viewpoints=viewpoints,
            min_required_frames=config["min_required_frames"],
            recommended_distance_m=config["recommended_distance_m"],
            notes=notes,
        )

        self.storage.save_capture_plan(plan)
        logger.info(
            f"Capture plan saved: {len(viewpoints)} viewpoints, "
            f"min {config['min_required_frames']} frames required"
        )

        return plan

    def load_plan(self) -> CapturePlan:
        """Load an existing capture plan.

        Returns:
            CapturePlan instance

        Raises:
            ConfigError: If the capture plan is not found
        """
        return self.storage.load_capture_plan()

    def _generate_notes(self, preset: CapturePlanPreset) -> list[str]:
        """Generate capture notes for the given preset.

        Args:
            preset: Capture plan preset type

        Returns:
            List of capture notes
        """
        base_notes = [
            "Ensure consistent lighting throughout the capture session.",
            "Keep the object stationary during capture.",
            "Maintain the recommended distance for optimal depth accuracy.",
        ]

        if preset == CapturePlanPreset.QUICK:
            return [
                *base_notes,
                "Quick mode: Suitable for simple objects with minimal occlusions.",
            ]
        elif preset == CapturePlanPreset.STANDARD:
            return [
                *base_notes,
                "Standard mode: Balanced coverage for most objects.",
                "Consider additional captures for areas with fine details.",
            ]
        else:  # HARD
            return [
                *base_notes,
                "Hard mode: Comprehensive coverage for complex objects.",
                "Multiple elevation angles help capture undercuts and overhangs.",
                "Take extra care with reflective or transparent surfaces.",
            ]
