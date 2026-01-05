"""Tests for scan2mesh.stages.plan module."""

from pathlib import Path

import pytest

from scan2mesh.exceptions import ConfigError
from scan2mesh.models import CapturePlan, CapturePlanPreset, ViewPoint
from scan2mesh.stages.init import ProjectInitializer
from scan2mesh.stages.plan import CapturePlanner


class TestCapturePlanner:
    """Tests for CapturePlanner class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test CapturePlanner initialization."""
        project_dir = tmp_path / "test_project"
        planner = CapturePlanner(project_dir)

        assert planner.project_dir == project_dir

    def test_preset_configs_exist(self) -> None:
        """Test that preset configurations are defined."""
        assert "num_azimuths" in CapturePlanner.QUICK_CONFIG
        assert "elevations" in CapturePlanner.QUICK_CONFIG
        assert "min_required_frames" in CapturePlanner.QUICK_CONFIG
        assert "recommended_distance_m" in CapturePlanner.QUICK_CONFIG

        assert "num_azimuths" in CapturePlanner.STANDARD_CONFIG
        assert "num_azimuths" in CapturePlanner.HARD_CONFIG


class TestGetViewpoints:
    """Tests for get_viewpoints method."""

    def test_quick_preset_viewpoint_count(self, tmp_path: Path) -> None:
        """Test QUICK preset generates correct number of viewpoints."""
        planner = CapturePlanner(tmp_path)
        viewpoints = planner.get_viewpoints(CapturePlanPreset.QUICK)

        # QUICK: 8 azimuths x 2 elevations = 16
        expected_count = 8 * 2
        assert len(viewpoints) == expected_count

    def test_standard_preset_viewpoint_count(self, tmp_path: Path) -> None:
        """Test STANDARD preset generates correct number of viewpoints."""
        planner = CapturePlanner(tmp_path)
        viewpoints = planner.get_viewpoints(CapturePlanPreset.STANDARD)

        # STANDARD: 12 azimuths x 3 elevations = 36
        expected_count = 12 * 3
        assert len(viewpoints) == expected_count

    def test_hard_preset_viewpoint_count(self, tmp_path: Path) -> None:
        """Test HARD preset generates correct number of viewpoints."""
        planner = CapturePlanner(tmp_path)
        viewpoints = planner.get_viewpoints(CapturePlanPreset.HARD)

        # HARD: 12 azimuths x 4 elevations = 48
        expected_count = 12 * 4
        assert len(viewpoints) == expected_count

    def test_azimuth_distribution(self, tmp_path: Path) -> None:
        """Test that azimuths are evenly distributed."""
        planner = CapturePlanner(tmp_path)
        viewpoints = planner.get_viewpoints(CapturePlanPreset.QUICK)

        # Get unique azimuths
        azimuths = sorted({v.azimuth_deg for v in viewpoints})

        # QUICK has 8 azimuths
        assert len(azimuths) == 8

        # Check even distribution (45 degree intervals)
        expected_azimuths = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]
        for expected, actual in zip(expected_azimuths, azimuths, strict=True):
            assert abs(expected - actual) < 0.01

    def test_azimuth_range(self, tmp_path: Path) -> None:
        """Test that all azimuths are in valid range."""
        planner = CapturePlanner(tmp_path)
        viewpoints = planner.get_viewpoints(CapturePlanPreset.STANDARD)

        for v in viewpoints:
            assert 0 <= v.azimuth_deg < 360

    def test_elevation_values(self, tmp_path: Path) -> None:
        """Test that elevations match preset configuration."""
        planner = CapturePlanner(tmp_path)
        viewpoints = planner.get_viewpoints(CapturePlanPreset.STANDARD)

        elevations = {v.elevation_deg for v in viewpoints}
        expected_elevations = {-15.0, 15.0, 45.0}
        assert elevations == expected_elevations

    def test_viewpoint_indices(self, tmp_path: Path) -> None:
        """Test that viewpoint indices are sequential."""
        planner = CapturePlanner(tmp_path)
        viewpoints = planner.get_viewpoints(CapturePlanPreset.QUICK)

        indices = [v.index for v in viewpoints]
        expected_indices = list(range(len(viewpoints)))
        assert indices == expected_indices

    def test_viewpoint_order(self, tmp_path: Path) -> None:
        """Test that viewpoint order matches index."""
        planner = CapturePlanner(tmp_path)
        viewpoints = planner.get_viewpoints(CapturePlanPreset.STANDARD)

        for v in viewpoints:
            assert v.order == v.index

    def test_viewpoint_distance(self, tmp_path: Path) -> None:
        """Test that viewpoint distance matches preset."""
        planner = CapturePlanner(tmp_path)
        viewpoints = planner.get_viewpoints(CapturePlanPreset.QUICK)

        expected_distance = CapturePlanner.QUICK_CONFIG["recommended_distance_m"]
        for v in viewpoints:
            assert v.distance_m == expected_distance

    def test_viewpoint_type(self, tmp_path: Path) -> None:
        """Test that viewpoints are ViewPoint instances."""
        planner = CapturePlanner(tmp_path)
        viewpoints = planner.get_viewpoints(CapturePlanPreset.STANDARD)

        for v in viewpoints:
            assert isinstance(v, ViewPoint)


class TestGeneratePlan:
    """Tests for generate_plan method."""

    def test_generate_plan_quick(self, tmp_path: Path) -> None:
        """Test generating plan with QUICK preset."""
        project_dir = tmp_path / "test_project"

        # Initialize project first
        initializer = ProjectInitializer(project_dir)
        initializer.initialize(object_name="test", class_id=0)

        # Generate plan
        planner = CapturePlanner(project_dir)
        plan = planner.generate_plan(CapturePlanPreset.QUICK)

        assert isinstance(plan, CapturePlan)
        assert plan.preset == CapturePlanPreset.QUICK
        assert len(plan.viewpoints) == 16

    def test_generate_plan_standard(self, tmp_path: Path) -> None:
        """Test generating plan with STANDARD preset."""
        project_dir = tmp_path / "test_project"

        initializer = ProjectInitializer(project_dir)
        initializer.initialize(object_name="test", class_id=0)

        planner = CapturePlanner(project_dir)
        plan = planner.generate_plan(CapturePlanPreset.STANDARD)

        assert plan.preset == CapturePlanPreset.STANDARD
        assert len(plan.viewpoints) == 36

    def test_generate_plan_hard(self, tmp_path: Path) -> None:
        """Test generating plan with HARD preset."""
        project_dir = tmp_path / "test_project"

        initializer = ProjectInitializer(project_dir)
        initializer.initialize(object_name="test", class_id=0)

        planner = CapturePlanner(project_dir)
        plan = planner.generate_plan(CapturePlanPreset.HARD)

        assert plan.preset == CapturePlanPreset.HARD
        assert len(plan.viewpoints) == 48

    def test_generate_plan_saves_file(self, tmp_path: Path) -> None:
        """Test that generate_plan saves capture_plan.json."""
        project_dir = tmp_path / "test_project"

        initializer = ProjectInitializer(project_dir)
        initializer.initialize(object_name="test", class_id=0)

        planner = CapturePlanner(project_dir)
        planner.generate_plan(CapturePlanPreset.STANDARD)

        capture_plan_path = project_dir / "capture_plan.json"
        assert capture_plan_path.exists()

    def test_generate_plan_min_required_frames(self, tmp_path: Path) -> None:
        """Test that min_required_frames is set correctly."""
        project_dir = tmp_path / "test_project"

        initializer = ProjectInitializer(project_dir)
        initializer.initialize(object_name="test", class_id=0)

        planner = CapturePlanner(project_dir)
        plan = planner.generate_plan(CapturePlanPreset.QUICK)

        assert (
            plan.min_required_frames
            == CapturePlanner.QUICK_CONFIG["min_required_frames"]
        )

    def test_generate_plan_recommended_distance(self, tmp_path: Path) -> None:
        """Test that recommended_distance_m is set correctly."""
        project_dir = tmp_path / "test_project"

        initializer = ProjectInitializer(project_dir)
        initializer.initialize(object_name="test", class_id=0)

        planner = CapturePlanner(project_dir)
        plan = planner.generate_plan(CapturePlanPreset.HARD)

        expected_distance = CapturePlanner.HARD_CONFIG["recommended_distance_m"]
        assert plan.recommended_distance_m == expected_distance

    def test_generate_plan_has_notes(self, tmp_path: Path) -> None:
        """Test that generate_plan includes notes."""
        project_dir = tmp_path / "test_project"

        initializer = ProjectInitializer(project_dir)
        initializer.initialize(object_name="test", class_id=0)

        planner = CapturePlanner(project_dir)
        plan = planner.generate_plan(CapturePlanPreset.STANDARD)

        assert len(plan.notes) > 0

    def test_generate_plan_uninitialized_project(self, tmp_path: Path) -> None:
        """Test that generate_plan raises error for uninitialized project."""
        project_dir = tmp_path / "nonexistent"

        planner = CapturePlanner(project_dir)

        with pytest.raises(ConfigError, match="not initialized"):
            planner.generate_plan(CapturePlanPreset.STANDARD)


class TestLoadPlan:
    """Tests for load_plan method."""

    def test_load_plan(self, tmp_path: Path) -> None:
        """Test loading an existing plan."""
        project_dir = tmp_path / "test_project"

        # Initialize and generate plan
        initializer = ProjectInitializer(project_dir)
        initializer.initialize(object_name="test", class_id=0)

        planner = CapturePlanner(project_dir)
        original = planner.generate_plan(CapturePlanPreset.STANDARD)

        # Load plan
        loaded = planner.load_plan()

        assert loaded.preset == original.preset
        assert len(loaded.viewpoints) == len(original.viewpoints)
        assert loaded.min_required_frames == original.min_required_frames

    def test_load_plan_preserves_viewpoints(self, tmp_path: Path) -> None:
        """Test that loading preserves viewpoint data."""
        project_dir = tmp_path / "test_project"

        initializer = ProjectInitializer(project_dir)
        initializer.initialize(object_name="test", class_id=0)

        planner = CapturePlanner(project_dir)
        original = planner.generate_plan(CapturePlanPreset.QUICK)

        loaded = planner.load_plan()

        for orig_v, loaded_v in zip(
            original.viewpoints, loaded.viewpoints, strict=True
        ):
            assert orig_v.index == loaded_v.index
            assert orig_v.azimuth_deg == loaded_v.azimuth_deg
            assert orig_v.elevation_deg == loaded_v.elevation_deg
            assert orig_v.distance_m == loaded_v.distance_m

    def test_load_plan_missing_file(self, tmp_path: Path) -> None:
        """Test that load_plan raises error when file doesn't exist."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        planner = CapturePlanner(project_dir)

        with pytest.raises(ConfigError, match="not found"):
            planner.load_plan()
