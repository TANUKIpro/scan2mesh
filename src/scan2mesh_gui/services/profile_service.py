"""Profile management service."""

from datetime import datetime
from pathlib import Path

from scan2mesh_gui.data.storage import ProfileStorage
from scan2mesh_gui.models.profile import Profile


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

    def export_profile(self, profile_id: str, output_path: Path) -> Path | None:
        """Export a profile to a ZIP file."""
        # TODO: Implement export
        raise NotImplementedError("Export not yet implemented")

    def import_profile(self, file_path: Path) -> Profile | None:
        """Import a profile from a ZIP file."""
        # TODO: Implement import
        raise NotImplementedError("Import not yet implemented")
