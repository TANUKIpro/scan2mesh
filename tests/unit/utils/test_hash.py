"""Tests for scan2mesh.utils.hash module."""

from datetime import datetime

from scan2mesh.models import OutputPreset, ScaleInfo
from scan2mesh.utils.hash import calculate_config_hash


class TestCalculateConfigHash:
    """Tests for calculate_config_hash function."""

    def test_basic_hash(self) -> None:
        """Test basic hash calculation."""
        config_data = {
            "object_name": "test_ball",
            "class_id": 42,
            "tags": ["test"],
        }
        hash_value = calculate_config_hash(config_data)

        assert isinstance(hash_value, str)
        assert len(hash_value) == 16  # First 16 chars of SHA256

    def test_deterministic(self) -> None:
        """Test that hashing is deterministic."""
        config_data = {
            "object_name": "test_ball",
            "class_id": 42,
        }
        hash1 = calculate_config_hash(config_data)
        hash2 = calculate_config_hash(config_data)

        assert hash1 == hash2

    def test_different_data_different_hash(self) -> None:
        """Test that different data produces different hashes."""
        config1 = {"object_name": "ball1", "class_id": 1}
        config2 = {"object_name": "ball2", "class_id": 1}

        hash1 = calculate_config_hash(config1)
        hash2 = calculate_config_hash(config2)

        assert hash1 != hash2

    def test_order_independence(self) -> None:
        """Test that key order doesn't affect hash."""
        config1 = {"a": 1, "b": 2, "c": 3}
        config2 = {"c": 3, "a": 1, "b": 2}

        hash1 = calculate_config_hash(config1)
        hash2 = calculate_config_hash(config2)

        assert hash1 == hash2

    def test_complex_data(self) -> None:
        """Test hashing complex nested data."""
        now = datetime.now()
        config_data = {
            "object_name": "test",
            "class_id": 0,
            "tags": ["a", "b"],
            "output_preset": OutputPreset(),
            "scale_info": ScaleInfo(method="realsense_depth_scale", uncertainty="low"),
            "created_at": now,
            "updated_at": now,
        }

        hash_value = calculate_config_hash(config_data)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16

    def test_timestamps_excluded(self) -> None:
        """Test that timestamps don't affect hash."""
        config1 = {
            "object_name": "test",
            "class_id": 0,
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 1),
        }
        config2 = {
            "object_name": "test",
            "class_id": 0,
            "created_at": datetime(2025, 1, 1),
            "updated_at": datetime(2025, 1, 1),
        }

        hash1 = calculate_config_hash(config1)
        hash2 = calculate_config_hash(config2)

        assert hash1 == hash2
