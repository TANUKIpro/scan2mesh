"""Package service for managing asset packaging sessions."""

import random
import uuid
from datetime import datetime
from pathlib import Path

from scan2mesh_gui.models.package_session import (
    STAGE_ORDER,
    PackageConfig,
    PackageMetrics,
    PackageSession,
    PackageStage,
)


class PackageService:
    """Service for managing asset packaging sessions."""

    def __init__(self, projects_dir: Path) -> None:
        """Initialize the package service.

        Args:
            projects_dir: Base directory for project data
        """
        self.projects_dir = projects_dir

    def start_session(
        self,
        object_id: str,
        object_name: str,
        config: PackageConfig,
    ) -> PackageSession:
        """Start a new packaging session.

        Args:
            object_id: ID of the object being packaged
            object_name: Name of the object being packaged
            config: Package configuration

        Returns:
            A new PackageSession
        """
        session_id = str(uuid.uuid4())[:8]

        return PackageSession(
            session_id=session_id,
            object_id=object_id,
            object_name=object_name,
            current_stage=PackageStage.IDLE,
            config=config,
            metrics=PackageMetrics(),
            is_running=True,
            started_at=datetime.now(),
        )

    def advance_stage(
        self,
        session: PackageSession,
    ) -> PackageSession:
        """Advance the session to the next stage.

        Args:
            session: The active package session

        Returns:
            Updated PackageSession with next stage
        """
        current_index = STAGE_ORDER.index(session.current_stage)

        # Check if already at final stage
        if session.current_stage == PackageStage.COMPLETE:
            return session

        # Get next stage
        next_stage = STAGE_ORDER[current_index + 1]

        # Skip CREATING_ARCHIVE if output format is directory
        if (
            next_stage == PackageStage.CREATING_ARCHIVE
            and session.config.output_format == "directory"
        ):
            next_stage = PackageStage.COMPLETE

        # Generate metrics and output path when reaching complete
        new_metrics = session.metrics
        is_running = session.is_running

        if next_stage == PackageStage.COMPLETE:
            new_metrics = self.generate_mock_metrics(
                session.config,
                session.object_name,
            )
            is_running = False

        return PackageSession(
            session_id=session.session_id,
            object_id=session.object_id,
            object_name=session.object_name,
            current_stage=next_stage,
            config=session.config,
            metrics=new_metrics,
            is_running=is_running,
            started_at=session.started_at,
        )

    def stop_session(
        self,
        session: PackageSession,
    ) -> PackageSession:
        """Stop a packaging session.

        Args:
            session: The packaging session to stop

        Returns:
            Updated PackageSession with is_running=False
        """
        return PackageSession(
            session_id=session.session_id,
            object_id=session.object_id,
            object_name=session.object_name,
            current_stage=session.current_stage,
            config=session.config,
            metrics=session.metrics,
            is_running=False,
            started_at=session.started_at,
        )

    def generate_mock_metrics(
        self,
        config: PackageConfig,
        object_name: str,
    ) -> PackageMetrics:
        """Generate mock metrics based on package configuration.

        Args:
            config: Package configuration
            object_name: Name of the object

        Returns:
            PackageMetrics with simulated values
        """
        files_included: list[str] = []
        total_size = 0

        # Add mesh files based on config
        if config.include_lod0:
            files_included.append(f"{object_name}_lod0.glb")
            total_size += random.randint(8_000_000, 12_000_000)  # 8-12 MB

        if config.include_lod1:
            files_included.append(f"{object_name}_lod1.glb")
            total_size += random.randint(2_000_000, 4_000_000)  # 2-4 MB

        if config.include_lod2:
            files_included.append(f"{object_name}_lod2.glb")
            total_size += random.randint(500_000, 1_500_000)  # 0.5-1.5 MB

        if config.include_collision:
            files_included.append(f"{object_name}_collision.glb")
            total_size += random.randint(50_000, 150_000)  # 50-150 KB

        if config.include_manifest:
            files_included.append("manifest.json")
            total_size += random.randint(2_000, 5_000)  # 2-5 KB

        if config.include_report:
            files_included.append("quality_report.json")
            total_size += random.randint(3_000, 8_000)  # 3-8 KB

        if config.include_preview:
            files_included.append("preview.png")
            files_included.append("thumbnail.png")
            total_size += random.randint(100_000, 300_000)  # 100-300 KB

        if config.include_source:
            files_included.append("source/frames.tar.gz")
            total_size += random.randint(50_000_000, 200_000_000)  # 50-200 MB

        # Calculate compressed size (ZIP only)
        compressed_size: int | None = None
        if config.output_format == "zip":
            # Assume 40-60% compression ratio
            compression_ratio = random.uniform(0.4, 0.6)
            compressed_size = int(total_size * compression_ratio)

        # Generate timestamp for output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if config.output_format == "zip":
            output_path = f"{config.output_dir}/{object_name}_{timestamp}.zip"
        else:
            output_path = f"{config.output_dir}/{object_name}_{timestamp}"

        return PackageMetrics(
            files_count=len(files_included),
            total_size_bytes=total_size,
            compressed_size_bytes=compressed_size,
            output_path=output_path,
            files_included=files_included,
        )

    def run_all_stages(
        self,
        session: PackageSession,
    ) -> PackageSession:
        """Run through all packaging stages.

        This is a convenience method that advances through all stages
        in sequence. In a real implementation, each stage would involve
        actual file operations.

        Args:
            session: The packaging session

        Returns:
            Completed PackageSession
        """
        current_session = session

        # Start from IDLE and advance to COLLECTING_ASSETS
        if current_session.current_stage == PackageStage.IDLE:
            current_session = self.advance_stage(current_session)

        # Continue advancing until complete
        while current_session.current_stage != PackageStage.COMPLETE:
            current_session = self.advance_stage(current_session)

        return current_session
