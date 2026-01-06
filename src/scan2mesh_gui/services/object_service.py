"""Scan object management service."""

import uuid
from datetime import datetime
from pathlib import Path

from scan2mesh_gui.data.storage import ObjectStorage
from scan2mesh_gui.models.scan_object import (
    PipelineStage,
    QualityStatus,
    ScanObject,
)


# Allowed image MIME types and extensions
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


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

    def get_status_counts(self, profile_id: str) -> dict[QualityStatus, int]:
        """Get counts of objects by quality status."""
        objects = self.storage.list_for_profile(profile_id)
        counts: dict[QualityStatus, int] = dict.fromkeys(QualityStatus, 0)
        for obj in objects:
            counts[obj.quality_status] += 1
        return counts

    def list_all_objects(
        self,
        profile_ids: list[str],
    ) -> list[ScanObject]:
        """List all objects across multiple profiles.

        Args:
            profile_ids: List of profile IDs to gather objects from.

        Returns:
            All objects from the specified profiles, sorted by updated_at (newest first).
        """
        all_objects: list[ScanObject] = []
        for profile_id in profile_ids:
            objects = self.storage.list_for_profile(profile_id)
            all_objects.extend(objects)
        return sorted(all_objects, key=lambda o: o.updated_at, reverse=True)

    def get_all_status_counts(
        self,
        profile_ids: list[str],
    ) -> dict[QualityStatus, int]:
        """Get counts of objects by quality status across multiple profiles.

        Args:
            profile_ids: List of profile IDs to gather statistics from.

        Returns:
            Dictionary mapping QualityStatus to count.
        """
        counts: dict[QualityStatus, int] = dict.fromkeys(QualityStatus, 0)
        for profile_id in profile_ids:
            objects = self.storage.list_for_profile(profile_id)
            for obj in objects:
                counts[obj.quality_status] += 1
        return counts

    def get_stage_counts(
        self,
        profile_ids: list[str],
    ) -> dict[PipelineStage, int]:
        """Get counts of objects by pipeline stage across multiple profiles.

        Args:
            profile_ids: List of profile IDs to gather statistics from.

        Returns:
            Dictionary mapping PipelineStage to count.
        """
        counts: dict[PipelineStage, int] = dict.fromkeys(PipelineStage, 0)
        for profile_id in profile_ids:
            objects = self.storage.list_for_profile(profile_id)
            for obj in objects:
                counts[obj.current_stage] += 1
        return counts

    def add_reference_image(
        self,
        profile_id: str,
        object_id: str,
        image_data: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> str:
        """Add a reference image to an object.

        Args:
            profile_id: The profile ID.
            object_id: The object ID.
            image_data: The image file content as bytes.
            filename: The original filename.
            mime_type: The MIME type (optional, will infer from extension).

        Returns:
            The relative path to the saved image.

        Raises:
            ValueError: If the image is invalid or too large.
        """
        # Validate file size
        if len(image_data) > MAX_IMAGE_SIZE_BYTES:
            raise ValueError(
                f"Image size exceeds maximum allowed ({MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB)"
            )

        # Validate MIME type
        if mime_type and mime_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError(
                f"Invalid image type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
            )

        # Validate and get file extension
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(
                f"Invalid file extension. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )

        # Load the object
        obj = self.get_object(profile_id, object_id)
        if not obj:
            raise ValueError(f"Object not found: {object_id}")

        # Create reference directory
        reference_dir = (
            self.profiles_dir / profile_id / "objects" / object_id / "reference"
        )
        reference_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"ref_{unique_id}{ext}"
        image_path = reference_dir / safe_filename

        # Save image
        image_path.write_bytes(image_data)

        # Update object
        relative_path = f"reference/{safe_filename}"
        obj.reference_images.append(relative_path)

        # Set preview image if this is the first image
        if obj.preview_image is None:
            obj.preview_image = relative_path

        obj.updated_at = datetime.now()
        self.storage.save_for_profile(profile_id, obj)

        return relative_path

    def delete_reference_image(
        self,
        profile_id: str,
        object_id: str,
        image_path: str,
    ) -> bool:
        """Delete a reference image from an object.

        Args:
            profile_id: The profile ID.
            object_id: The object ID.
            image_path: The relative path to the image (e.g., "reference/ref_abc123.png").

        Returns:
            True if the image was deleted, False otherwise.
        """
        obj = self.get_object(profile_id, object_id)
        if not obj:
            return False

        # Security check: ensure the path is within the object's reference directory
        if ".." in image_path or not image_path.startswith("reference/"):
            return False

        # Remove from reference_images list
        if image_path not in obj.reference_images:
            return False

        obj.reference_images.remove(image_path)

        # Update preview_image if needed
        if obj.preview_image == image_path:
            obj.preview_image = obj.reference_images[0] if obj.reference_images else None

        # Delete the actual file
        full_path = (
            self.profiles_dir / profile_id / "objects" / object_id / image_path
        )
        if full_path.exists():
            full_path.unlink()

        obj.updated_at = datetime.now()
        self.storage.save_for_profile(profile_id, obj)

        return True

    def get_reference_image_path(
        self,
        profile_id: str,
        object_id: str,
        relative_path: str,
    ) -> Path | None:
        """Get the full path to a reference image.

        Args:
            profile_id: The profile ID.
            object_id: The object ID.
            relative_path: The relative path to the image.

        Returns:
            The full path to the image, or None if it doesn't exist.
        """
        # Security check
        if ".." in relative_path:
            return None

        full_path = (
            self.profiles_dir / profile_id / "objects" / object_id / relative_path
        )
        if full_path.exists():
            return full_path
        return None
