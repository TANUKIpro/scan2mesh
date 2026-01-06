"""CLI commands for scan2mesh.

This module provides the command implementations for the scan2mesh CLI.
"""

from pathlib import Path
from typing import Annotated

import typer

from scan2mesh.cli.display import (
    display_capture_result,
    display_error,
    display_init_result,
    display_not_implemented,
    display_plan_result,
)
from scan2mesh.cli.validators import (
    validate_class_id,
    validate_dimension,
    validate_object_name,
    validate_project_dir,
)
from scan2mesh.exceptions import NotImplementedStageError, Scan2MeshError
from scan2mesh.models import CapturePlanPreset
from scan2mesh.orchestrator import PipelineOrchestrator


def init(
    name: Annotated[
        str,
        typer.Option(
            "--name",
            "-n",
            help="Name of the object to scan (letters, numbers, underscores, hyphens)",
        ),
    ],
    class_id: Annotated[
        int,
        typer.Option(
            "--class-id",
            "-c",
            help="Class ID for the object (0-9999)",
        ),
    ],
    project_dir: Annotated[
        Path | None,
        typer.Option(
            "--project-dir",
            "-d",
            help="Base directory for projects (default: ./projects)",
        ),
    ] = None,
    tags: Annotated[
        str | None,
        typer.Option(
            "--tags",
            "-t",
            help="Comma-separated list of tags",
        ),
    ] = None,
    dimension: Annotated[
        float | None,
        typer.Option(
            "--dimension",
            help="Known dimension in millimeters",
        ),
    ] = None,
    dimension_type: Annotated[
        str | None,
        typer.Option(
            "--dimension-type",
            help="Type of known dimension (width, height, depth, diameter)",
        ),
    ] = None,
) -> None:
    """Initialize a new scan2mesh project.

    Creates a project directory with the required structure and configuration.
    """
    try:
        # Validate inputs
        validated_name = validate_object_name(name)
        validated_class_id = validate_class_id(class_id)
        validated_base_dir = validate_project_dir(project_dir)
        validated_dimension = validate_dimension(dimension)

        # Parse tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        # Build project path
        project_path = validated_base_dir / validated_name

        # Run init stage
        orchestrator = PipelineOrchestrator(project_path)
        config = orchestrator.run_init(
            object_name=validated_name,
            class_id=validated_class_id,
            tags=tag_list,
            known_dimension_mm=validated_dimension,
            dimension_type=dimension_type,
        )

        # Display result
        display_init_result(config, str(project_path))

    except Scan2MeshError as e:
        display_error(str(e))
        raise typer.Exit(1) from e


def plan(
    project_dir: Annotated[
        Path,
        typer.Argument(help="Path to the project directory"),
    ],
    preset: Annotated[
        str,
        typer.Option(
            "--preset",
            "-p",
            help="Capture plan preset (quick, standard, hard)",
        ),
    ] = "standard",
) -> None:
    """Create a capture plan for the project.

    Generates optimal camera viewpoints for 3D reconstruction.
    """
    try:
        # Validate preset
        preset_lower = preset.lower()
        preset_map = {
            "quick": CapturePlanPreset.QUICK,
            "standard": CapturePlanPreset.STANDARD,
            "hard": CapturePlanPreset.HARD,
        }
        if preset_lower not in preset_map:
            display_error(
                f"Invalid preset: {preset}. Must be one of: quick, standard, hard"
            )
            raise typer.Exit(1)

        capture_preset = preset_map[preset_lower]

        orchestrator = PipelineOrchestrator(project_dir)
        capture_plan = orchestrator.run_plan(capture_preset)
        display_plan_result(capture_plan, str(project_dir))
    except NotImplementedStageError:
        display_not_implemented("plan")
        raise typer.Exit(1) from None
    except Scan2MeshError as e:
        display_error(str(e))
        raise typer.Exit(1) from e


def capture(
    project_dir: Annotated[
        Path,
        typer.Argument(help="Path to the project directory"),
    ],
    num_frames: Annotated[
        int,
        typer.Option(
            "--num-frames",
            "-n",
            help="Number of frames to capture",
        ),
    ] = 30,
    use_mock: Annotated[
        bool,
        typer.Option(
            "--mock",
            help="Use mock camera for testing",
        ),
    ] = False,
) -> None:
    """Capture RGBD frames using RealSense camera.

    Captures depth and color frames following the capture plan.
    """
    try:
        orchestrator = PipelineOrchestrator(project_dir)
        metrics, status, suggestions = orchestrator.run_capture(
            num_frames=num_frames,
            use_mock=use_mock,
        )
        display_capture_result(metrics, status, str(project_dir), suggestions)
    except NotImplementedStageError:
        display_not_implemented("capture")
        raise typer.Exit(1) from None
    except Scan2MeshError as e:
        display_error(str(e))
        raise typer.Exit(1) from e


def preprocess(
    project_dir: Annotated[
        Path,
        typer.Argument(help="Path to the project directory"),
    ],
) -> None:
    """Preprocess captured frames.

    Selects keyframes and creates background masks.
    """
    try:
        orchestrator = PipelineOrchestrator(project_dir)
        orchestrator.run_preprocess()
    except NotImplementedStageError:
        display_not_implemented("preprocess")
        raise typer.Exit(1) from None
    except Scan2MeshError as e:
        display_error(str(e))
        raise typer.Exit(1) from e


def reconstruct(
    project_dir: Annotated[
        Path,
        typer.Argument(help="Path to the project directory"),
    ],
) -> None:
    """Reconstruct 3D mesh from preprocessed frames.

    Performs pose estimation, point cloud generation, and mesh reconstruction.
    """
    try:
        orchestrator = PipelineOrchestrator(project_dir)
        orchestrator.run_reconstruct()
    except NotImplementedStageError:
        display_not_implemented("reconstruct")
        raise typer.Exit(1) from None
    except Scan2MeshError as e:
        display_error(str(e))
        raise typer.Exit(1) from e


def optimize(
    project_dir: Annotated[
        Path,
        typer.Argument(help="Path to the project directory"),
    ],
) -> None:
    """Optimize reconstructed mesh.

    Simplifies mesh, generates LODs, and creates collision mesh.
    """
    try:
        orchestrator = PipelineOrchestrator(project_dir)
        orchestrator.run_optimize()
    except NotImplementedStageError:
        display_not_implemented("optimize")
        raise typer.Exit(1) from None
    except Scan2MeshError as e:
        display_error(str(e))
        raise typer.Exit(1) from e


def package(
    project_dir: Annotated[
        Path,
        typer.Argument(help="Path to the project directory"),
    ],
) -> None:
    """Package optimized assets for distribution.

    Exports GLB/GLTF and creates asset manifest.
    """
    try:
        orchestrator = PipelineOrchestrator(project_dir)
        orchestrator.run_package()
    except NotImplementedStageError:
        display_not_implemented("package")
        raise typer.Exit(1) from None
    except Scan2MeshError as e:
        display_error(str(e))
        raise typer.Exit(1) from e


def report(
    project_dir: Annotated[
        Path,
        typer.Argument(help="Path to the project directory"),
    ],
) -> None:
    """Generate quality report.

    Collects metrics and generates comprehensive quality assessment.
    """
    try:
        orchestrator = PipelineOrchestrator(project_dir)
        orchestrator.run_report()
    except NotImplementedStageError:
        display_not_implemented("report")
        raise typer.Exit(1) from None
    except Scan2MeshError as e:
        display_error(str(e))
        raise typer.Exit(1) from e
