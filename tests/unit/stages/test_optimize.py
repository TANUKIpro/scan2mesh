"""Tests for AssetOptimizer."""

import numpy as np
import pytest

from scan2mesh.stages.optimize import AssetOptimizer


class TestNormalizeAxes:
    """Tests for normalize_axes method."""

    def test_normalize_axes_bottom_center_origin(self, tmp_path):
        """Test that origin is moved to bottom center."""
        # Create a simple cube mesh
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ], dtype=np.float64)

        # Create project config
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create minimal project.json
        import json
        config = {
            "schema_version": "1.0",
            "object_name": "test",
            "class_id": 1,
            "tags": [],
            "output_preset": {
                "coordinate_system": {
                    "up_axis": "Z",
                    "forward_axis": "Y",
                    "origin": "bottom_center",
                },
                "units": "meter",
                "texture_resolution": 2048,
                "lod_triangle_limits": [100000, 30000, 10000],
            },
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "config_hash": "abc123",
        }
        (project_dir / "project.json").write_text(json.dumps(config))

        optimizer = AssetOptimizer(project_dir)
        normalized = optimizer.normalize_axes(vertices)

        # Check that bottom center is at origin
        min_z = np.min(normalized[:, 2])
        assert min_z == pytest.approx(0.0, abs=1e-10)

        center_x = (np.min(normalized[:, 0]) + np.max(normalized[:, 0])) / 2
        center_y = (np.min(normalized[:, 1]) + np.max(normalized[:, 1])) / 2
        assert center_x == pytest.approx(0.0, abs=1e-10)
        assert center_y == pytest.approx(0.0, abs=1e-10)

    def test_normalize_axes_empty_vertices(self, tmp_path):
        """Test that empty vertices are handled."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        import json
        config = {
            "schema_version": "1.0",
            "object_name": "test",
            "class_id": 1,
            "tags": [],
            "output_preset": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "config_hash": "abc123",
        }
        (project_dir / "project.json").write_text(json.dumps(config))

        optimizer = AssetOptimizer(project_dir)
        empty_vertices = np.array([], dtype=np.float64).reshape(0, 3)
        result = optimizer.normalize_axes(empty_vertices)

        assert len(result) == 0


class TestApplyScale:
    """Tests for apply_scale method."""

    def test_apply_scale_with_known_dimension(self, tmp_path):
        """Test scale application with known dimension."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        import json
        config = {
            "schema_version": "1.0",
            "object_name": "test",
            "class_id": 1,
            "tags": [],
            "output_preset": {},
            "scale_info": {
                "method": "known_dimension",
                "known_dimension_mm": 100.0,  # 100mm diameter
                "dimension_type": "diameter",
                "uncertainty": "low",
            },
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "config_hash": "abc123",
        }
        (project_dir / "project.json").write_text(json.dumps(config))

        # Create mesh with diameter of 2 units
        vertices = np.array([
            [-1, 0, 0],
            [1, 0, 0],
            [0, -1, 0],
            [0, 1, 0],
        ], dtype=np.float64)

        optimizer = AssetOptimizer(project_dir)
        scaled, uncertainty = optimizer.apply_scale(vertices)

        # After scaling, diameter should be 0.1m (100mm)
        new_diameter = np.max(scaled[:, 0]) - np.min(scaled[:, 0])
        assert new_diameter == pytest.approx(0.1, abs=0.001)
        assert uncertainty == "low"

    def test_apply_scale_without_scale_info(self, tmp_path):
        """Test scale when no scale info is provided."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        import json
        config = {
            "schema_version": "1.0",
            "object_name": "test",
            "class_id": 1,
            "tags": [],
            "output_preset": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "config_hash": "abc123",
        }
        (project_dir / "project.json").write_text(json.dumps(config))

        vertices = np.array([[0, 0, 0], [1, 0, 0]], dtype=np.float64)

        optimizer = AssetOptimizer(project_dir)
        scaled, uncertainty = optimizer.apply_scale(vertices)

        # Vertices should be unchanged
        np.testing.assert_array_almost_equal(scaled, vertices)
        assert uncertainty == "high"


class TestRepairMesh:
    """Tests for repair_mesh method."""

    def test_repair_mesh_no_changes_needed(self, tmp_path):
        """Test repair on clean mesh."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        import json
        config = {
            "schema_version": "1.0",
            "object_name": "test",
            "class_id": 1,
            "tags": [],
            "output_preset": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "config_hash": "abc123",
        }
        (project_dir / "project.json").write_text(json.dumps(config))

        # Simple triangle
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0.5, 1, 0],
        ], dtype=np.float64)
        triangles = np.array([[0, 1, 2]], dtype=np.int64)

        optimizer = AssetOptimizer(project_dir)
        repaired_v, repaired_t, _non_manifold = optimizer.repair_mesh(vertices, triangles)

        # Should have same number of vertices and triangles
        assert len(repaired_v) == len(vertices)
        assert len(repaired_t) == len(triangles)


class TestGenerateLod:
    """Tests for generate_lod method."""

    def test_generate_lod_no_simplification_needed(self, tmp_path):
        """Test LOD when mesh is already small."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        import json
        config = {
            "schema_version": "1.0",
            "object_name": "test",
            "class_id": 1,
            "tags": [],
            "output_preset": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "config_hash": "abc123",
        }
        (project_dir / "project.json").write_text(json.dumps(config))

        # Very small mesh
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0.5, 1, 0],
        ], dtype=np.float64)
        triangles = np.array([[0, 1, 2]], dtype=np.int64)

        optimizer = AssetOptimizer(project_dir)
        _lod_v, lod_t = optimizer.generate_lod(vertices, triangles, target_triangles=1000)

        # No simplification needed
        assert len(lod_t) == len(triangles)


class TestGenerateCollision:
    """Tests for generate_collision method."""

    def test_generate_collision_convex_hull(self, tmp_path):
        """Test convex hull generation."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        import json
        config = {
            "schema_version": "1.0",
            "object_name": "test",
            "class_id": 1,
            "tags": [],
            "output_preset": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "config_hash": "abc123",
        }
        (project_dir / "project.json").write_text(json.dumps(config))

        # Create a box shape
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ], dtype=np.float64)

        optimizer = AssetOptimizer(project_dir)
        hull_v, _hull_t, num_parts = optimizer.generate_collision(vertices)

        # Should generate a convex hull
        assert len(hull_v) > 0
        assert num_parts >= 0  # Depends on library availability


class TestCalculateBoundingBox:
    """Tests for _calculate_bounding_box method."""

    def test_calculate_bounding_box_unit_cube(self, tmp_path):
        """Test bounding box calculation for unit cube."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        import json
        config = {
            "schema_version": "1.0",
            "object_name": "test",
            "class_id": 1,
            "tags": [],
            "output_preset": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "config_hash": "abc123",
        }
        (project_dir / "project.json").write_text(json.dumps(config))

        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ], dtype=np.float64)

        optimizer = AssetOptimizer(project_dir)
        aabb, _obb = optimizer._calculate_bounding_box(vertices)

        assert aabb == pytest.approx([1.0, 1.0, 1.0], abs=1e-6)

    def test_calculate_bounding_box_empty(self, tmp_path):
        """Test bounding box for empty mesh."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        import json
        config = {
            "schema_version": "1.0",
            "object_name": "test",
            "class_id": 1,
            "tags": [],
            "output_preset": {},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "config_hash": "abc123",
        }
        (project_dir / "project.json").write_text(json.dumps(config))

        empty_vertices = np.array([], dtype=np.float64).reshape(0, 3)

        optimizer = AssetOptimizer(project_dir)
        aabb, obb = optimizer._calculate_bounding_box(empty_vertices)

        assert aabb == [0.0, 0.0, 0.0]
        assert obb == [0.0, 0.0, 0.0]
