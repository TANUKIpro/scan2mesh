"""Storage layer for JSON-based data persistence."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

from scan2mesh_gui.models.profile import Profile
from scan2mesh_gui.models.scan_object import ScanObject


T = TypeVar("T", bound=BaseModel)


class BaseStorage(ABC, Generic[T]):
    """Base class for JSON file storage."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def get_path(self, item_id: str) -> Path:
        """Get the file path for an item."""
        ...

    def save(self, item: T, item_id: str) -> None:
        """Save an item to disk atomically."""
        path = self.get_path(item_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(item.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        temp_path.rename(path)

    def load(self, item_id: str, model_class: type[T]) -> T | None:
        """Load an item from disk."""
        path = self.get_path(item_id)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return model_class(**data)

    def delete(self, item_id: str) -> bool:
        """Delete an item from disk."""
        path = self.get_path(item_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, item_id: str) -> bool:
        """Check if an item exists."""
        return self.get_path(item_id).exists()


class ProfileStorage(BaseStorage[Profile]):
    """Storage for Profile data."""

    def get_path(self, profile_id: str) -> Path:
        return self.base_dir / profile_id / "profile.json"

    def list_all(self) -> list[Profile]:
        """List all profiles."""
        profiles: list[Profile] = []
        for profile_dir in self.base_dir.iterdir():
            if profile_dir.is_dir():
                profile = self.load(profile_dir.name, Profile)
                if profile:
                    profiles.append(profile)
        return sorted(profiles, key=lambda p: p.updated_at, reverse=True)

    def get_profile_dir(self, profile_id: str) -> Path:
        """Get the directory for a profile."""
        return self.base_dir / profile_id


class ObjectStorage(BaseStorage[ScanObject]):
    """Storage for ScanObject data."""

    def __init__(self, profiles_dir: Path) -> None:
        self.profiles_dir = profiles_dir

    def get_path(self, object_id: str) -> Path:
        # Objects are stored within their profile directory
        # This requires knowing the profile_id, which we handle differently
        raise NotImplementedError("Use get_path_for_profile instead")

    def get_path_for_profile(self, profile_id: str, object_id: str) -> Path:
        """Get the file path for an object within a profile."""
        return self.profiles_dir / profile_id / "objects" / object_id / "object.json"

    def save_for_profile(self, profile_id: str, obj: ScanObject) -> None:
        """Save an object within a profile."""
        path = self.get_path_for_profile(profile_id, obj.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(obj.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        temp_path.rename(path)

    def load_for_profile(self, profile_id: str, object_id: str) -> ScanObject | None:
        """Load an object from a profile."""
        path = self.get_path_for_profile(profile_id, object_id)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return ScanObject(**data)

    def list_for_profile(self, profile_id: str) -> list[ScanObject]:
        """List all objects in a profile."""
        objects: list[ScanObject] = []
        objects_dir = self.profiles_dir / profile_id / "objects"
        if not objects_dir.exists():
            return objects
        for obj_dir in objects_dir.iterdir():
            if obj_dir.is_dir():
                obj = self.load_for_profile(profile_id, obj_dir.name)
                if obj:
                    objects.append(obj)
        return sorted(objects, key=lambda o: o.updated_at, reverse=True)

    def delete_for_profile(self, profile_id: str, object_id: str) -> bool:
        """Delete an object from a profile."""
        path = self.get_path_for_profile(profile_id, object_id)
        if path.exists():
            # Delete the entire object directory
            import shutil
            shutil.rmtree(path.parent)
            return True
        return False
