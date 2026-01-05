"""Hash calculation utilities."""

import hashlib
import json
from datetime import datetime
from typing import Any


def calculate_config_hash(config_data: dict[str, Any]) -> str:
    """Calculate a deterministic hash of configuration data.

    This hash is used to ensure reproducibility - the same configuration
    will always produce the same hash, allowing users to verify that
    outputs were generated from identical settings.

    Args:
        config_data: Configuration dictionary to hash.
            Excludes timestamp fields (created_at, updated_at) and
            the config_hash field itself.

    Returns:
        SHA256 hash as a hex string (first 16 characters).

    Example:
        >>> data = {"object_name": "ball", "class_id": 0}
        >>> hash_value = calculate_config_hash(data)
        >>> len(hash_value)
        16
    """
    # Create a copy to avoid modifying the original
    data_to_hash = _prepare_data_for_hash(config_data)

    # Convert to canonical JSON string
    json_str = json.dumps(data_to_hash, sort_keys=True, ensure_ascii=True)

    # Calculate SHA256 hash
    hash_bytes = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    # Return first 16 characters
    return hash_bytes[:16]


def _prepare_data_for_hash(data: dict[str, Any]) -> dict[str, Any]:
    """Prepare data for hashing by removing volatile fields.

    Args:
        data: Input dictionary

    Returns:
        Dictionary with volatile fields removed
    """
    result: dict[str, Any] = {}

    for key, value in data.items():
        # Skip volatile fields
        if key in ("created_at", "updated_at", "config_hash"):
            continue

        # Handle nested dictionaries
        if isinstance(value, dict):
            result[key] = _prepare_data_for_hash(value)
        # Handle datetime objects
        elif isinstance(value, datetime):
            continue  # Skip datetime fields
        # Handle lists
        elif isinstance(value, list):
            result[key] = [
                _prepare_data_for_hash(item) if isinstance(item, dict) else item
                for item in value
            ]
        # Handle Pydantic models (they have model_dump method)
        elif hasattr(value, "model_dump"):
            result[key] = _prepare_data_for_hash(value.model_dump())
        else:
            result[key] = value

    return result
