"""Reconstruct service for managing 3D reconstruction sessions."""

import random
import uuid
from datetime import datetime
from pathlib import Path

from scan2mesh_gui.models.reconstruct_session import (
    STAGE_ORDER,
    ReconstructMetrics,
    ReconstructSession,
    ReconstructStage,
)


class ReconstructService:
    """Service for managing 3D reconstruction sessions."""

    def __init__(self, projects_dir: Path) -> None:
        """Initialize the reconstruct service.

        Args:
            projects_dir: Base directory for project data
        """
        self.projects_dir = projects_dir

    def start_session(
        self,
        object_id: str,
        input_frames: int,
    ) -> ReconstructSession:
        """Start a new reconstruction session.

        Args:
            object_id: ID of the object being reconstructed
            input_frames: Number of input masked frames

        Returns:
            A new ReconstructSession
        """
        session_id = str(uuid.uuid4())[:8]

        return ReconstructSession(
            session_id=session_id,
            object_id=object_id,
            input_frames=input_frames,
            current_stage=ReconstructStage.IDLE,
            metrics=ReconstructMetrics(),
            is_running=True,
            output_mesh_path=None,
            started_at=datetime.now(),
        )

    def advance_stage(
        self,
        session: ReconstructSession,
    ) -> ReconstructSession:
        """Advance the session to the next stage.

        Args:
            session: The active reconstruct session

        Returns:
            Updated ReconstructSession with next stage
        """
        current_index = STAGE_ORDER.index(session.current_stage)

        # Check if already at final stage
        if session.current_stage == ReconstructStage.COMPLETE:
            return session

        # Get next stage
        next_stage = STAGE_ORDER[current_index + 1]

        # Generate metrics and output path when reaching complete
        new_metrics = session.metrics
        output_path = session.output_mesh_path
        is_running = session.is_running

        if next_stage == ReconstructStage.COMPLETE:
            new_metrics = self.generate_mock_metrics(session.input_frames)
            output_path = str(
                self.projects_dir
                / session.object_id
                / "recon"
                / "mesh.ply"
            )
            is_running = False

        return ReconstructSession(
            session_id=session.session_id,
            object_id=session.object_id,
            input_frames=session.input_frames,
            current_stage=next_stage,
            metrics=new_metrics,
            is_running=is_running,
            output_mesh_path=output_path,
            started_at=session.started_at,
        )

    def get_stage_progress(self, stage: ReconstructStage) -> float:
        """Get progress ratio for a given stage.

        Args:
            stage: The reconstruction stage

        Returns:
            Progress ratio (0.0-1.0) for the stage
        """
        if stage == ReconstructStage.IDLE:
            return 0.0
        if stage == ReconstructStage.COMPLETE:
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
        session: ReconstructSession,
    ) -> ReconstructSession:
        """Stop a reconstruction session.

        Args:
            session: The reconstruction session to stop

        Returns:
            Updated ReconstructSession with is_running=False
        """
        return ReconstructSession(
            session_id=session.session_id,
            object_id=session.object_id,
            input_frames=session.input_frames,
            current_stage=session.current_stage,
            metrics=session.metrics,
            is_running=False,
            output_mesh_path=session.output_mesh_path,
            started_at=session.started_at,
        )

    def generate_mock_metrics(self, input_frames: int) -> ReconstructMetrics:
        """Generate mock metrics based on input frame count.

        Args:
            input_frames: Number of input masked frames

        Returns:
            ReconstructMetrics with simulated values
        """
        # Simulate vertex/triangle counts based on frame count
        base_vertices = 30000 + input_frames * 500
        vertex_variation = int(base_vertices * 0.1)
        num_vertices = base_vertices + random.randint(-vertex_variation, vertex_variation)

        # Triangles are roughly 2x vertices
        num_triangles = int(num_vertices * 1.9) + random.randint(-1000, 1000)

        # Texture resolution based on quality
        texture_res = 2048 if input_frames > 30 else 1024

        # File size estimate (roughly 100 bytes per vertex)
        file_size = num_vertices * 100 + num_triangles * 20

        # Coverage improves with more frames
        base_coverage = min(0.95, 0.7 + input_frames * 0.007)
        coverage = base_coverage + random.uniform(-0.05, 0.05)
        coverage = max(0.5, min(1.0, coverage))

        # Keyframes used (95% of input frames)
        keyframes_used = int(input_frames * 0.95)

        # Tracking loss (2-5% of frames)
        tracking_loss = max(0, input_frames - keyframes_used)

        return ReconstructMetrics(
            num_vertices=num_vertices,
            num_triangles=num_triangles,
            texture_resolution=(texture_res, texture_res),
            file_size_bytes=file_size,
            is_watertight=random.random() > 0.2,  # 80% chance watertight
            num_holes=random.randint(0, 3),
            surface_coverage=coverage,
            keyframes_used=keyframes_used,
            tracking_loss_frames=tracking_loss,
        )

    def run_all_stages(
        self,
        session: ReconstructSession,
    ) -> ReconstructSession:
        """Run through all reconstruction stages.

        This is a convenience method that advances through all stages
        in sequence. In a real implementation, each stage would involve
        actual processing.

        Args:
            session: The reconstruction session

        Returns:
            Completed ReconstructSession
        """
        current_session = session

        # Start from IDLE and advance to FEATURE_EXTRACTION
        if current_session.current_stage == ReconstructStage.IDLE:
            current_session = self.advance_stage(current_session)

        # Continue advancing until complete
        while current_session.current_stage != ReconstructStage.COMPLETE:
            current_session = self.advance_stage(current_session)

        return current_session
