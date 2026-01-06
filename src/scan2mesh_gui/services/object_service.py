"""Scan object management service."""

from datetime import datetime
from pathlib import Path

from scan2mesh_gui.data.storage import ObjectStorage
from scan2mesh_gui.models.scan_object import PipelineStage, QualityStatus, ScanObject


class ObjectService:
    """Service for managing scan objects."""

    def __init__(self, profiles_dir: Path, projects_dir: Path) -> None:
        self.profiles_dir = profiles_dir
        self.projects_dir = projects_dir
        self.storage = ObjectStorage(profiles_dir)

    def list_objects(
        self,
        profile_id: str,
        filter_stage: PipelineStage | None = None,
        filter_status: QualityStatus | None = None,
    ) -> list[ScanObject]:
        """List objects in a profile with optional filters."""
        objects = self.storage.list_for_profile(profile_id)

        if filter_stage:
            objects = [o for o in objects if o.current_stage == filter_stage]
        if filter_status:
            objects = [o for o in objects if o.quality_status == filter_status]

        return objects

    def get_object(self, profile_id: str, object_id: str) -> ScanObject | None:
        """Get an object by ID."""
        return self.storage.load_for_profile(profile_id, object_id)

    def create_object(
        self,
        profile_id: str,
        name: str,
        display_name: str,
        class_id: int,
        tags: list[str] | None = None,
        known_dimension_mm: float | None = None,
        dimension_type: str | None = None,
    ) -> ScanObject:
        """Create a new scan object."""
        obj = ScanObject(
            profile_id=profile_id,
            name=name,
            display_name=display_name,
            class_id=class_id,
            tags=tags or [],
            known_dimension_mm=known_dimension_mm,
            dimension_type=dimension_type,
        )
        self.storage.save_for_profile(profile_id, obj)
        return obj

    def update_object(
        self,
        profile_id: str,
        object_id: str,
        **kwargs: object,
    ) -> ScanObject | None:
        """Update an object."""
        obj = self.get_object(profile_id, object_id)
        if not obj:
            return None

        for key, value in kwargs.items():
            if hasattr(obj, key) and value is not None:
                setattr(obj, key, value)
        obj.updated_at = datetime.now()

        self.storage.save_for_profile(profile_id, obj)
        return obj

    def delete_object(self, profile_id: str, object_id: str) -> bool:
        """Delete an object."""
        return self.storage.delete_for_profile(profile_id, object_id)

    def update_stage(
        self,
        profile_id: str,
        object_id: str,
        stage: PipelineStage,
        status: QualityStatus | None = None,
    ) -> ScanObject | None:
        """Update the pipeline stage of an object."""
        obj = self.get_object(profile_id, object_id)
        if not obj:
            return None

        obj.current_stage = stage
        if status:
            obj.quality_status = status
        obj.updated_at = datetime.now()

        self.storage.save_for_profile(profile_id, obj)
        return obj

    def get_object_count(self, profile_id: str) -> int:
        """Get the number of objects in a profile."""
        return len(self.storage.list_for_profile(profile_id))

    def get_status_counts(
        self, profile_id: str
    ) -> dict[QualityStatus, int]:
        """Get counts of objects by quality status."""
        objects = self.storage.list_for_profile(profile_id)
        counts: dict[QualityStatus, int] = dict.fromkeys(QualityStatus, 0)
        for obj in objects:
            counts[obj.quality_status] += 1
        return counts
