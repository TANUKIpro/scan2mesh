"""Optimize service for managing mesh optimization sessions."""

import random
import uuid
from datetime import datetime
from pathlib import Path

from scan2mesh_gui.models.optimize_session import (
    STAGE_ORDER,
    OptimizeMetrics,
    OptimizeSession,
    OptimizeStage,
)


class OptimizeService:
    """Service for managing mesh optimization sessions."""

    def __init__(self, projects_dir: Path) -> None:
        """Initialize the optimize service.

        Args:
            projects_dir: Base directory for project data
        """
        self.projects_dir = projects_dir

    def start_session(
        self,
        object_id: str,
        input_mesh_path: str | None,
        input_vertices: int,
        input_triangles: int,
        lod0_target: int = 100000,
        lod1_target: int = 30000,
        lod2_target: int = 10000,
    ) -> OptimizeSession:
        """Start a new optimization session.

        Args:
            object_id: ID of the object being optimized
            input_mesh_path: Path to input mesh file
            input_vertices: Number of input mesh vertices
            input_triangles: Number of input mesh triangles
            lod0_target: Target triangle count for LOD0
            lod1_target: Target triangle count for LOD1
            lod2_target: Target triangle count for LOD2

        Returns:
            A new OptimizeSession
        """
        session_id = str(uuid.uuid4())[:8]

        return OptimizeSession(
            session_id=session_id,
            object_id=object_id,
            input_mesh_path=input_mesh_path,
            input_vertices=input_vertices,
            input_triangles=input_triangles,
            current_stage=OptimizeStage.IDLE,
            metrics=OptimizeMetrics(),
            is_running=True,
            output_dir=None,
            started_at=datetime.now(),
            lod0_target=lod0_target,
            lod1_target=lod1_target,
            lod2_target=lod2_target,
        )

    def advance_stage(
        self,
        session: OptimizeSession,
    ) -> OptimizeSession:
        """Advance the session to the next stage.

        Args:
            session: The active optimize session

        Returns:
            Updated OptimizeSession with next stage
        """
        current_index = STAGE_ORDER.index(session.current_stage)

        # Check if already at final stage
        if session.current_stage == OptimizeStage.COMPLETE:
            return session

        # Get next stage
        next_stage = STAGE_ORDER[current_index + 1]

        # Generate metrics and output path when reaching complete
        new_metrics = session.metrics
        output_dir = session.output_dir
        is_running = session.is_running

        if next_stage == OptimizeStage.COMPLETE:
            new_metrics = self.generate_mock_metrics(
                session.input_triangles,
                (session.lod0_target, session.lod1_target, session.lod2_target),
            )
            output_dir = str(
                self.projects_dir / session.object_id / "asset"
            )
            is_running = False

        return OptimizeSession(
            session_id=session.session_id,
            object_id=session.object_id,
            input_mesh_path=session.input_mesh_path,
            input_vertices=session.input_vertices,
            input_triangles=session.input_triangles,
            current_stage=next_stage,
            metrics=new_metrics,
            is_running=is_running,
            output_dir=output_dir,
            started_at=session.started_at,
            lod0_target=session.lod0_target,
            lod1_target=session.lod1_target,
            lod2_target=session.lod2_target,
        )

    def get_stage_progress(self, stage: OptimizeStage) -> float:
        """Get progress ratio for a given stage.

        Args:
            stage: The optimization stage

        Returns:
            Progress ratio (0.0-1.0) for the stage
        """
        if stage == OptimizeStage.IDLE:
            return 0.0
        if stage == OptimizeStage.COMPLETE:
            return 1.0

        try:
            stage_index = STAGE_ORDER.index(stage)
            # Exclude IDLE and COMPLETE from calculation
            total_stages = len(STAGE_ORDER) - 2  # 5 working stages
            return stage_index / total_stages
        except ValueError:
            return 0.0

    def stop_session(
        self,
        session: OptimizeSession,
    ) -> OptimizeSession:
        """Stop an optimization session.

        Args:
            session: The optimization session to stop

        Returns:
            Updated OptimizeSession with is_running=False
        """
        return OptimizeSession(
            session_id=session.session_id,
            object_id=session.object_id,
            input_mesh_path=session.input_mesh_path,
            input_vertices=session.input_vertices,
            input_triangles=session.input_triangles,
            current_stage=session.current_stage,
            metrics=session.metrics,
            is_running=False,
            output_dir=session.output_dir,
            started_at=session.started_at,
            lod0_target=session.lod0_target,
            lod1_target=session.lod1_target,
            lod2_target=session.lod2_target,
        )

    def generate_mock_metrics(
        self,
        input_triangles: int,
        lod_limits: tuple[int, int, int],
    ) -> OptimizeMetrics:
        """Generate mock metrics based on input triangle count.

        Args:
            input_triangles: Number of input mesh triangles
            lod_limits: Target triangle counts for (LOD0, LOD1, LOD2)

        Returns:
            OptimizeMetrics with simulated values
        """
        lod0_target, lod1_target, lod2_target = lod_limits

        # LOD0: use target or input if smaller
        lod0_triangles = min(input_triangles, lod0_target)
        lod0_triangles += random.randint(-100, 100)  # Small variation
        lod0_triangles = max(1000, lod0_triangles)

        # LOD1 and LOD2 are always simplified
        lod1_triangles = min(lod0_triangles, lod1_target)
        lod1_triangles += random.randint(-50, 50)
        lod1_triangles = max(500, lod1_triangles)

        lod2_triangles = min(lod1_triangles, lod2_target)
        lod2_triangles += random.randint(-20, 20)
        lod2_triangles = max(100, lod2_triangles)

        # Collision mesh: very simple
        collision_triangles = max(64, lod2_triangles // 10)
        collision_triangles += random.randint(-10, 10)
        collision_triangles = max(32, collision_triangles)

        # Scale factor (usually close to 1.0)
        scale_factor = 1.0 + random.uniform(-0.05, 0.1)

        # Mesh cleaning metrics
        holes_filled = random.randint(0, 5)
        components_removed = random.randint(0, 3)

        # Texture resolution based on input size
        if input_triangles > 50000:
            texture_resolution = (2048, 2048)
        elif input_triangles > 20000:
            texture_resolution = (1024, 1024)
        else:
            texture_resolution = (512, 512)

        # Output size estimate
        base_size = lod0_triangles * 50 + lod1_triangles * 50 + lod2_triangles * 50
        texture_size = texture_resolution[0] * texture_resolution[1] * 3  # RGB
        output_size_bytes = base_size + texture_size

        # Bounding box (simulated dimensions in meters)
        dim_base = 0.15 + random.uniform(0.0, 0.2)  # 15-35cm base
        bounding_box = (
            round(dim_base + random.uniform(-0.02, 0.02), 3),
            round(dim_base + random.uniform(-0.02, 0.02), 3),
            round(dim_base + random.uniform(-0.02, 0.05), 3),
        )

        return OptimizeMetrics(
            scale_factor=round(scale_factor, 4),
            holes_filled=holes_filled,
            components_removed=components_removed,
            lod0_triangles=lod0_triangles,
            lod1_triangles=lod1_triangles,
            lod2_triangles=lod2_triangles,
            collision_triangles=collision_triangles,
            texture_resolution=texture_resolution,
            output_size_bytes=output_size_bytes,
            bounding_box=bounding_box,
        )

    def run_all_stages(
        self,
        session: OptimizeSession,
    ) -> OptimizeSession:
        """Run through all optimization stages.

        This is a convenience method that advances through all stages
        in sequence. In a real implementation, each stage would involve
        actual processing.

        Args:
            session: The optimization session

        Returns:
            Completed OptimizeSession
        """
        current_session = session

        # Start from IDLE and advance to SCALE_CALIBRATION
        if current_session.current_stage == OptimizeStage.IDLE:
            current_session = self.advance_stage(current_session)

        # Continue advancing until complete
        while current_session.current_stage != OptimizeStage.COMPLETE:
            current_session = self.advance_stage(current_session)

        return current_session
