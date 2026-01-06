"""Tests for Packager."""

import json
import zipfile
from pathlib import Path

import pytest

from scan2mesh.models import PackageResult
from scan2mesh.stages.package import Packager


def create_project_config(project_dir: Path) -> None:
    """Create a valid project.json file."""
    config = {
        "schema_version": "1.0",
        "object_name": "test_object",
        "class_id": 42,
        "tags": ["test", "sample"],
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
        "scale_info": {
            "method": "known_dimension",
            "known_dimension_mm": 100.0,
            "dimension_type": "diameter",
            "uncertainty": "low",
        },
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
        "config_hash": "abc123def456",
    }
    (project_dir / "project.json").write_text(json.dumps(config))


def create_capture_metrics(project_dir: Path, gate_status: str = "pass") -> None:
    """Create capture_metrics.json file."""
    metrics = {
        "num_frames_raw": 30,
        "num_keyframes": 20,
        "depth_valid_ratio_mean": 0.9,
        "depth_valid_ratio_min": 0.8,
        "blur_score_mean": 0.85,
        "blur_score_min": 0.7,
        "coverage_score": 0.9,
        "capture_duration_sec": 60.0,
        "gate_status": gate_status,
        "gate_reasons": [] if gate_status == "pass" else ["Test reason"],
    }
    (project_dir / "capture_metrics.json").write_text(json.dumps(metrics))


def create_recon_report(project_dir: Path, gate_status: str = "pass") -> None:
    """Create recon_report.json file."""
    report = {
        "num_frames_used": 20,
        "tracking_success_rate": 0.95,
        "alignment_rmse_mean": 0.005,
        "alignment_rmse_max": 0.01,
        "drift_indicator": 0.02,
        "poses": [],
        "tsdf_voxel_size": 0.002,
        "mesh_vertices": 50000,
        "mesh_triangles": 100000,
        "processing_time_sec": 120.0,
        "gate_status": gate_status,
        "gate_reasons": [] if gate_status == "pass" else ["Test reason"],
    }
    (project_dir / "recon_report.json").write_text(json.dumps(report))


def create_asset_metrics(project_dir: Path, gate_status: str = "pass") -> None:
    """Create asset_metrics.json file."""
    metrics = {
        "lod_metrics": [
            {"level": 0, "triangles": 100000, "vertices": 50000, "file_size_bytes": 1024000},
            {"level": 1, "triangles": 30000, "vertices": 15000, "file_size_bytes": 512000},
            {"level": 2, "triangles": 10000, "vertices": 5000, "file_size_bytes": 256000},
        ],
        "collision_metrics": {
            "method": "convex_hull",
            "num_convex_parts": 1,
            "total_triangles": 100,
        },
        "aabb_size": [0.1, 0.1, 0.1],
        "obb_size": [0.1, 0.1, 0.1],
        "hole_area_ratio": 0.01,
        "non_manifold_edges": 0,
        "texture_resolution": 2048,
        "texture_coverage": 0.95,
        "scale_uncertainty": "low",
        "gate_status": gate_status,
        "gate_reasons": [] if gate_status == "pass" else ["Test reason"],
    }
    (project_dir / "asset_metrics.json").write_text(json.dumps(metrics))


def create_asset_files(project_dir: Path) -> None:
    """Create dummy asset files."""
    asset_dir = project_dir / "asset"
    asset_dir.mkdir(exist_ok=True)

    # Create dummy GLB files (minimal binary content)
    for filename in ["lod0.glb", "lod1.glb", "lod2.glb", "collision.glb"]:
        (asset_dir / filename).write_bytes(b"dummy glb content")

    # Create dummy preview image
    (asset_dir / "preview.png").write_bytes(b"dummy png content")


class TestBuildProvenance:
    """Tests for _build_provenance method."""

    def test_build_provenance_returns_correct_structure(self, tmp_path: Path) -> None:
        """Test that provenance has correct fields."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)

        packager = Packager(project_dir)
        provenance = packager._build_provenance()

        assert provenance.device == "RealSense"
        assert provenance.tool_version == "0.1.0"
        assert provenance.config_hash == "abc123def456"
        # Date should be in YYYY-MM-DD format
        assert len(provenance.date) == 10
        assert "-" in provenance.date


class TestBuildFileReferences:
    """Tests for _build_file_references method."""

    def test_build_file_references_returns_correct_paths(self, tmp_path: Path) -> None:
        """Test that file references point to correct files."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)

        packager = Packager(project_dir)
        file_refs = packager._build_file_references()

        assert file_refs.visual_lod0 == "lod0.glb"
        assert file_refs.visual_lod1 == "lod1.glb"
        assert file_refs.visual_lod2 == "lod2.glb"
        assert file_refs.collision == "collision.glb"
        assert file_refs.preview == "preview.png"


class TestCalculateOverallStatus:
    """Tests for _calculate_overall_status method."""

    def test_all_pass_returns_pass(self, tmp_path: Path) -> None:
        """Test that all pass statuses result in overall pass."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir, "pass")
        create_recon_report(project_dir, "pass")
        create_asset_metrics(project_dir, "pass")

        packager = Packager(project_dir)
        status = packager._calculate_overall_status()

        assert status.status == "pass"
        assert len(status.reasons) == 0

    def test_one_warn_returns_warn(self, tmp_path: Path) -> None:
        """Test that one warn status results in overall warn."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir, "warn")
        create_recon_report(project_dir, "pass")
        create_asset_metrics(project_dir, "pass")

        packager = Packager(project_dir)
        status = packager._calculate_overall_status()

        assert status.status == "warn"
        assert len(status.reasons) > 0
        assert "Capture" in status.reasons[0]

    def test_one_fail_returns_fail(self, tmp_path: Path) -> None:
        """Test that one fail status results in overall fail."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir, "pass")
        create_recon_report(project_dir, "fail")
        create_asset_metrics(project_dir, "pass")

        packager = Packager(project_dir)
        status = packager._calculate_overall_status()

        assert status.status == "fail"
        assert len(status.reasons) > 0
        assert "Recon" in status.reasons[0]

    def test_fail_takes_precedence_over_warn(self, tmp_path: Path) -> None:
        """Test that fail takes precedence over warn."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir, "warn")
        create_recon_report(project_dir, "pass")
        create_asset_metrics(project_dir, "fail")

        packager = Packager(project_dir)
        status = packager._calculate_overall_status()

        assert status.status == "fail"


class TestBuildManifest:
    """Tests for _build_manifest method."""

    def test_build_manifest_includes_all_fields(self, tmp_path: Path) -> None:
        """Test that manifest contains all required fields."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir)
        create_recon_report(project_dir)
        create_asset_metrics(project_dir)

        packager = Packager(project_dir)
        manifest = packager._build_manifest()

        assert manifest.schema_version == "1.0"
        assert manifest.object_name == "test_object"
        assert manifest.class_id == 42
        assert manifest.units == "meter"
        assert manifest.files is not None
        assert manifest.provenance is not None
        assert manifest.quality is not None
        assert manifest.capture_metrics is not None
        assert manifest.recon_metrics is not None
        assert manifest.asset_metrics is not None


class TestCreateBundleStructure:
    """Tests for _create_bundle_structure method."""

    def test_create_bundle_copies_files(self, tmp_path: Path) -> None:
        """Test that bundle structure is created with files."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_asset_files(project_dir)

        packager = Packager(project_dir)
        files_copied = packager._create_bundle_structure()

        # Check files were copied
        output_dir = project_dir / "output"
        assert output_dir.exists()
        assert len(files_copied) == 5
        assert "lod0.glb" in files_copied
        assert "preview.png" in files_copied

        # Verify files exist
        for filename in files_copied:
            assert (output_dir / filename).exists()

    def test_create_bundle_handles_missing_files(self, tmp_path: Path) -> None:
        """Test that missing files are handled gracefully."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        # Create only some asset files
        asset_dir = project_dir / "asset"
        asset_dir.mkdir()
        (asset_dir / "lod0.glb").write_bytes(b"content")

        packager = Packager(project_dir)
        files_copied = packager._create_bundle_structure()

        # Only lod0.glb should be copied
        assert len(files_copied) == 1
        assert "lod0.glb" in files_copied


class TestCreateArchive:
    """Tests for _create_archive method."""

    def test_create_archive_produces_valid_zip(self, tmp_path: Path) -> None:
        """Test that a valid ZIP archive is created."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)

        # Create output directory with files
        output_dir = project_dir / "output"
        output_dir.mkdir()
        (output_dir / "test.txt").write_text("test content")
        (output_dir / "manifest.json").write_text('{"test": true}')

        packager = Packager(project_dir)
        archive_path, archive_size = packager._create_archive("test_object", 42)

        assert archive_path.name == "test_object_42.zip"
        assert archive_path.exists()
        assert archive_size > 0

        # Verify ZIP contents
        with zipfile.ZipFile(archive_path, "r") as zf:
            names = zf.namelist()
            assert "test.txt" in names
            assert "manifest.json" in names


class TestPackage:
    """Integration tests for package method."""

    def test_package_creates_complete_bundle(self, tmp_path: Path) -> None:
        """Test full packaging workflow."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir)
        create_recon_report(project_dir)
        create_asset_metrics(project_dir)
        create_asset_files(project_dir)

        packager = Packager(project_dir)
        result = packager.package()

        # Verify result structure
        assert isinstance(result, PackageResult)
        assert result.archive_path == "test_object_42.zip"
        assert result.output_dir == "output"
        assert result.total_size_bytes > 0
        assert "manifest.json" in result.files_included
        assert "lod0.glb" in result.files_included

        # Verify files were created
        assert (project_dir / "test_object_42.zip").exists()
        assert (project_dir / "output" / "manifest.json").exists()

        # Verify ZIP contents
        archive_path = project_dir / "test_object_42.zip"
        with zipfile.ZipFile(archive_path, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "lod0.glb" in names

    def test_package_fails_without_asset_metrics(self, tmp_path: Path) -> None:
        """Test that packaging fails without required metrics."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        create_project_config(project_dir)
        create_capture_metrics(project_dir)
        create_recon_report(project_dir)
        # Missing asset_metrics.json
        create_asset_files(project_dir)

        packager = Packager(project_dir)
        from scan2mesh.exceptions import ConfigError
        with pytest.raises(ConfigError):
            packager.package()
