"""Profile management service."""

import io
import json
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from scan2mesh_gui.data.storage import ProfileStorage
from scan2mesh_gui.models.profile import Profile
from scan2mesh_gui.models.scan_object import ScanObject


class ProfileService:
    """Service for managing profiles."""

    def __init__(self, profiles_dir: Path) -> None:
        self.profiles_dir = profiles_dir
        self.storage = ProfileStorage(profiles_dir)

    def list_profiles(self) -> list[Profile]:
        """Get all profiles."""
        return self.storage.list_all()

    def get_profile(self, profile_id: str) -> Profile | None:
        """Get a profile by ID."""
        return self.storage.load(profile_id, Profile)

    def create_profile(
        self,
        name: str,
        description: str = "",
        tags: list[str] | None = None,
    ) -> Profile:
        """Create a new profile."""
        profile = Profile(
            name=name,
            description=description if description else None,
            tags=tags or [],
        )
        self.storage.save(profile, profile.id)
        return profile

    def update_profile(
        self,
        profile_id: str,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> Profile | None:
        """Update a profile."""
        profile = self.get_profile(profile_id)
        if not profile:
            return None

        if name is not None:
            profile.name = name
        if description is not None:
            profile.description = description
        if tags is not None:
            profile.tags = tags
        profile.updated_at = datetime.now()

        self.storage.save(profile, profile.id)
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile and all its objects."""
        profile_dir = self.storage.get_profile_dir(profile_id)
        if profile_dir.exists():
            import shutil
            shutil.rmtree(profile_dir)
            return True
        return False

    def export_profile(self, profile_id: str) -> bytes | None:
        """Export a profile to a ZIP file in memory.

        Args:
            profile_id: The ID of the profile to export.

        Returns:
            ZIP file contents as bytes, or None if profile not found.
        """
        profile_dir = self.storage.get_profile_dir(profile_id)
        if not profile_dir.exists():
            return None

        # Create ZIP in memory
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in profile_dir.rglob("*"):
                if file_path.is_file():
                    # Store with relative path from profile_dir
                    arcname = file_path.relative_to(profile_dir)
                    zf.write(file_path, arcname)

        buffer.seek(0)
        return buffer.getvalue()

    def import_profile(self, zip_data: bytes | io.BytesIO) -> Profile:
        """Import a profile from a ZIP file.

        Args:
            zip_data: ZIP file contents as bytes or BytesIO.

        Returns:
            The imported Profile with new IDs.

        Raises:
            ValueError: If ZIP is invalid or doesn't contain valid profile data.
            zipfile.BadZipFile: If the file is not a valid ZIP.
        """
        if isinstance(zip_data, bytes):
            zip_data = io.BytesIO(zip_data)

        # Validate ZIP file
        if not zipfile.is_zipfile(zip_data):
            raise ValueError("Invalid ZIP file")

        zip_data.seek(0)

        with zipfile.ZipFile(zip_data, "r") as zf:
            # Check for profile.json
            if "profile.json" not in zf.namelist():
                raise ValueError("ZIP must contain profile.json")

            # Check for path traversal attacks
            for name in zf.namelist():
                if name.startswith("/") or ".." in name:
                    raise ValueError(f"Invalid path in ZIP: {name}")

            # Extract to temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                zf.extractall(temp_path)

                # Load and validate profile
                profile_json_path = temp_path / "profile.json"
                with profile_json_path.open(encoding="utf-8") as f:
                    profile_data = json.load(f)

                # Validate profile data
                old_profile = Profile(**profile_data)

                # Generate new IDs
                new_profile_id = str(uuid.uuid4())
                new_profile = Profile(
                    id=new_profile_id,
                    name=old_profile.name,
                    description=old_profile.description,
                    tags=old_profile.tags,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )

                # Create new profile directory
                new_profile_dir = self.profiles_dir / new_profile_id
                new_profile_dir.mkdir(parents=True, exist_ok=True)

                # Save new profile.json
                self.storage.save(new_profile, new_profile_id)

                # Process objects directory if exists
                objects_dir = temp_path / "objects"
                if objects_dir.exists():
                    new_objects_dir = new_profile_dir / "objects"
                    new_objects_dir.mkdir(exist_ok=True)

                    for old_obj_dir in objects_dir.iterdir():
                        if not old_obj_dir.is_dir():
                            continue

                        object_json_path = old_obj_dir / "object.json"
                        if not object_json_path.exists():
                            continue

                        # Load old object
                        with object_json_path.open(encoding="utf-8") as f:
                            obj_data = json.load(f)

                        old_object = ScanObject(**obj_data)

                        # Generate new object ID
                        new_object_id = str(uuid.uuid4())
                        new_object = ScanObject(
                            id=new_object_id,
                            profile_id=new_profile_id,
                            name=old_object.name,
                            display_name=old_object.display_name,
                            class_id=old_object.class_id,
                            tags=old_object.tags,
                            known_dimension_mm=old_object.known_dimension_mm,
                            dimension_type=old_object.dimension_type,
                            reference_images=[],  # Will be updated below
                            preview_image=None,
                            current_stage=old_object.current_stage,
                            quality_status=old_object.quality_status,
                            project_path=None,
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                        )

                        # Create new object directory
                        new_obj_dir = new_objects_dir / new_object_id
                        new_obj_dir.mkdir(exist_ok=True)

                        # Copy reference images if exist
                        old_ref_dir = old_obj_dir / "reference"
                        if old_ref_dir.exists():
                            new_ref_dir = new_obj_dir / "reference"
                            shutil.copytree(old_ref_dir, new_ref_dir)

                            # Update reference image paths
                            new_ref_images = []
                            for img_path in new_ref_dir.iterdir():
                                if img_path.is_file():
                                    rel_path = f"reference/{img_path.name}"
                                    new_ref_images.append(rel_path)
                            new_object.reference_images = new_ref_images

                        # Save new object.json
                        new_object_json_path = new_obj_dir / "object.json"
                        with new_object_json_path.open("w", encoding="utf-8") as f:
                            json.dump(
                                new_object.model_dump(mode="json"),
                                f,
                                indent=2,
                                ensure_ascii=False,
                            )

                return new_profile
