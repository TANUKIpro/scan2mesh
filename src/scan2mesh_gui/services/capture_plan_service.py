"""Capture plan service for generating and managing capture plans."""

import json
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from scan2mesh_gui.models.capture_plan import (
    CapturePlan,
    CapturePlanPreset,
    ViewPoint,
)


class CapturePlanService:
    """Service for generating and managing capture plans."""

    # Preset configurations: (azimuth_positions, elevation_levels, min_frames)
    PRESET_CONFIGS: ClassVar[dict[CapturePlanPreset, tuple[int, int, int]]] = {
        CapturePlanPreset.QUICK: (6, 3, 10),  # 18 viewpoints
        CapturePlanPreset.STANDARD: (6, 6, 20),  # 36 viewpoints
        CapturePlanPreset.HIGH_QUALITY: (6, 12, 40),  # 72 viewpoints
    }

    # Preset time estimates
    PRESET_TIME_ESTIMATES: ClassVar[dict[CapturePlanPreset, str]] = {
        CapturePlanPreset.QUICK: "1-2 minutes",
        CapturePlanPreset.STANDARD: "3-5 minutes",
        CapturePlanPreset.HIGH_QUALITY: "6-10 minutes",
    }

    def __init__(self, projects_dir: Path) -> None:
        """Initialize the capture plan service.

        Args:
            projects_dir: Directory for project data.
        """
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def generate_plan(
        self,
        preset: CapturePlanPreset,
        object_id: str | None = None,  # noqa: ARG002 Reserved for future use
        recommended_distance_m: float = 0.3,
    ) -> CapturePlan:
        """Generate a capture plan based on the preset.

        Args:
            preset: The capture plan preset to use.
            object_id: Optional object ID (for future use).
            recommended_distance_m: Recommended capture distance in meters.

        Returns:
            Generated CapturePlan.
        """
        config = self.PRESET_CONFIGS[preset]
        azimuth_positions, elevation_levels, min_frames = config

        viewpoints = self._generate_viewpoints(
            azimuth_positions=azimuth_positions,
            elevation_levels=elevation_levels,
            distance_m=recommended_distance_m,
        )

        notes = self._generate_notes(preset)

        return CapturePlan(
            preset=preset,
            viewpoints=viewpoints,
            min_required_frames=min_frames,
            recommended_distance_m=recommended_distance_m,
            notes=notes,
            created_at=datetime.now(),
        )

    def _generate_viewpoints(
        self,
        azimuth_positions: int,
        elevation_levels: int,
        distance_m: float,
    ) -> list[ViewPoint]:
        """Generate viewpoints in a spherical grid pattern.

        Args:
            azimuth_positions: Number of azimuth positions (around object).
            elevation_levels: Number of elevation levels (vertical).
            distance_m: Distance from object center.

        Returns:
            List of ViewPoint objects.
        """
        viewpoints: list[ViewPoint] = []
        index = 0

        # Calculate elevation angles (from 0 to 150 degrees for better coverage)
        elevation_start = 0
        elevation_end = 150
        elevation_step = (
            (elevation_end - elevation_start) / (elevation_levels - 1)
            if elevation_levels > 1
            else 0
        )

        # Calculate azimuth angles (0 to 360 degrees)
        azimuth_step = 360 / azimuth_positions

        for elev_idx in range(elevation_levels):
            elevation = elevation_start + elev_idx * elevation_step

            for az_idx in range(azimuth_positions):
                # Offset alternating elevation levels for better coverage
                offset = (azimuth_step / 2) if (elev_idx % 2 == 1) else 0
                azimuth = (az_idx * azimuth_step + offset) % 360

                viewpoints.append(
                    ViewPoint(
                        index=index,
                        azimuth_deg=round(azimuth, 1),
                        elevation_deg=round(elevation - 90, 1),  # Convert to -90 to 60
                        distance_m=distance_m,
                        order=index,
                    )
                )
                index += 1

        return viewpoints

    def _generate_notes(self, preset: CapturePlanPreset) -> list[str]:
        """Generate notes for the capture plan.

        Args:
            preset: The capture plan preset.

        Returns:
            List of notes/tips for the user.
        """
        notes = [
            "Keep the object centered in frame",
            "Move the camera slowly and steadily",
            "Ensure consistent lighting",
        ]

        if preset == CapturePlanPreset.QUICK:
            notes.append("Quick preset - suitable for simple objects")
        elif preset == CapturePlanPreset.STANDARD:
            notes.append("Standard preset - balanced coverage for most objects")
        elif preset == CapturePlanPreset.HIGH_QUALITY:
            notes.append("High quality preset - detailed coverage for complex objects")
            notes.append("Consider using a turntable for consistent rotation")

        return notes

    def get_preset_info(self, preset: CapturePlanPreset) -> dict[str, int | str]:
        """Get information about a preset.

        Args:
            preset: The capture plan preset.

        Returns:
            Dictionary with preset information.
        """
        config = self.PRESET_CONFIGS[preset]
        azimuth_positions, elevation_levels, min_frames = config
        viewpoint_count = azimuth_positions * elevation_levels

        return {
            "keyframes": viewpoint_count,
            "azimuth_positions": azimuth_positions,
            "elevation_levels": elevation_levels,
            "min_frames": min_frames,
            "time_estimate": self.PRESET_TIME_ESTIMATES[preset],
        }

    def save_plan(self, plan: CapturePlan, project_path: Path) -> None:
        """Save a capture plan to a project directory.

        Args:
            plan: The capture plan to save.
            project_path: Path to the project directory.

        Raises:
            ValueError: If project_path contains invalid characters.
        """
        # Validate path (security check)
        if ".." in str(project_path):
            raise ValueError("Invalid project path")

        project_path = Path(project_path)
        project_path.mkdir(parents=True, exist_ok=True)

        plan_file = project_path / "capture_plan.json"

        # Convert to dict for JSON serialization
        plan_dict = plan.model_dump(mode="json")

        with plan_file.open("w", encoding="utf-8") as f:
            json.dump(plan_dict, f, indent=2, ensure_ascii=False)

    def load_plan(self, project_path: Path) -> CapturePlan | None:
        """Load a capture plan from a project directory.

        Args:
            project_path: Path to the project directory.

        Returns:
            CapturePlan if found, None otherwise.
        """
        plan_file = Path(project_path) / "capture_plan.json"

        if not plan_file.exists():
            return None

        with plan_file.open("r", encoding="utf-8") as f:
            plan_dict = json.load(f)

        return CapturePlan(**plan_dict)

    @staticmethod
    def get_elevation_angles(preset: CapturePlanPreset) -> list[int]:
        """Get elevation angles for a preset.

        Args:
            preset: The capture plan preset.

        Returns:
            List of elevation angles in degrees.
        """
        config = CapturePlanService.PRESET_CONFIGS[preset]
        _, elevation_levels, _ = config

        # Generate elevation angles from 0 to 150
        if elevation_levels == 1:
            return [75]  # Single middle angle

        step = 150 / (elevation_levels - 1)
        return [int(i * step) for i in range(elevation_levels)]
