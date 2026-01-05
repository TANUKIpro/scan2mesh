"""Tests for scan2mesh.utils.file module."""

from pathlib import Path

import pytest

from scan2mesh.exceptions import StorageError
from scan2mesh.utils.file import load_json, save_json_atomic


class TestSaveJsonAtomic:
    """Tests for save_json_atomic function."""

    def test_save_basic(self, tmp_path: Path) -> None:
        """Test basic JSON save."""
        file_path = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        save_json_atomic(file_path, data)

        assert file_path.exists()
        content = file_path.read_text()
        assert '"key": "value"' in content
        assert '"number": 42' in content

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test that save creates parent directories."""
        file_path = tmp_path / "nested" / "dir" / "test.json"
        data = {"test": True}

        save_json_atomic(file_path, data)

        assert file_path.exists()

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        """Test that save overwrites existing file."""
        file_path = tmp_path / "test.json"
        file_path.write_text('{"old": "data"}')

        save_json_atomic(file_path, {"new": "data"})

        loaded = load_json(file_path)
        assert loaded == {"new": "data"}

    def test_save_formatted(self, tmp_path: Path) -> None:
        """Test that JSON is properly formatted."""
        file_path = tmp_path / "test.json"
        save_json_atomic(file_path, {"a": 1, "b": 2})

        content = file_path.read_text()
        # Should be indented
        assert "\n" in content


class TestLoadJson:
    """Tests for load_json function."""

    def test_load_basic(self, tmp_path: Path) -> None:
        """Test basic JSON load."""
        file_path = tmp_path / "test.json"
        file_path.write_text('{"key": "value", "number": 42}')

        data = load_json(file_path)

        assert data == {"key": "value", "number": 42}

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading nonexistent file raises error."""
        file_path = tmp_path / "nonexistent.json"

        with pytest.raises(StorageError, match="not found"):
            load_json(file_path)

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        """Test loading invalid JSON raises error."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("not valid json {")

        with pytest.raises(StorageError, match="Invalid JSON"):
            load_json(file_path)

    def test_load_empty_file(self, tmp_path: Path) -> None:
        """Test loading empty file raises error."""
        file_path = tmp_path / "empty.json"
        file_path.write_text("")

        with pytest.raises(StorageError):
            load_json(file_path)
