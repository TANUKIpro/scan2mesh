"""Package page - export final asset bundle."""

import time

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.package_session import (
    STAGE_ORDER,
    PackageConfig,
    PackageSession,
    PackageStage,
)
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.package_service import PackageService


def render_package() -> None:
    """Render the package page."""
    st.title("Package")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry", key="package_go_registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Packaging **{selected_object.display_name}**")

    # Initialize config and service
    config = get_config_manager()
    package_service = PackageService(config.projects_dir)

    # Initialize session state
    if "package_session" not in st.session_state:
        st.session_state.package_session = None

    # Get input information from optimize session
    optimize_session = st.session_state.get("optimize_session")
    if optimize_session is not None and optimize_session.is_complete:
        lod0_triangles = optimize_session.metrics.lod0_triangles
        lod1_triangles = optimize_session.metrics.lod1_triangles
        lod2_triangles = optimize_session.metrics.lod2_triangles
        collision_triangles = optimize_session.metrics.collision_triangles
        texture_res = optimize_session.metrics.texture_resolution
        total_size = optimize_session.metrics.output_size_bytes
    else:
        # Fallback values if no optimize session
        lod0_triangles = 89412
        lod1_triangles = 30000
        lod2_triangles = 10000
        collision_triangles = 512
        texture_res = (2048, 2048)
        total_size = 15_200_000

    # Asset summary
    st.subheader("Asset Summary")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("LOD Levels", "3")
    with col2:
        size_mb = total_size / (1024 * 1024)
        st.metric("Total Size", f"{size_mb:.1f} MB")
    with col3:
        st.metric("Texture Size", f"{texture_res[0]}x{texture_res[1]}")
    with col4:
        st.metric("Has Collision", "Yes" if collision_triangles > 0 else "No")

    st.divider()

    # Package contents preview
    st.subheader("Package Contents")

    st.markdown(f"""
    ```
    {selected_object.name}/
    ├── meshes/
    │   ├── {selected_object.name}_lod0.glb       # High detail ({lod0_triangles:,} triangles)
    │   ├── {selected_object.name}_lod1.glb       # Medium detail ({lod1_triangles:,} triangles)
    │   ├── {selected_object.name}_lod2.glb       # Low detail ({lod2_triangles:,} triangles)
    │   └── {selected_object.name}_collision.glb  # Collision mesh ({collision_triangles:,} triangles)
    │
    ├── textures/
    │   ├── {selected_object.name}_albedo.png     # {texture_res[0]}x{texture_res[1]}
    │   └── {selected_object.name}_normal.png     # {texture_res[0]}x{texture_res[1]} (optional)
    │
    ├── metadata/
    │   ├── manifest.json                # Asset manifest
    │   ├── quality_report.json          # Quality metrics
    │   └── capture_info.json            # Capture parameters
    │
    └── preview/
        ├── thumbnail.png                # 256x256
        └── preview.png                  # 512x512
    ```
    """)

    st.divider()

    # Export options
    st.subheader("Export Options")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Output Format**")
        export_format = st.selectbox(
            "Format",
            ["zip", "directory"],
            format_func=lambda x: {
                "directory": "Directory (uncompressed)",
                "zip": "ZIP Archive (compressed)",
            }.get(x, x),
            label_visibility="collapsed",
            key="package_format",
        )

        st.markdown("**Include**")
        include_lod0 = st.checkbox("LOD0 (High)", value=True, key="package_lod0")
        include_lod1 = st.checkbox("LOD1 (Medium)", value=True, key="package_lod1")
        include_lod2 = st.checkbox("LOD2 (Low)", value=True, key="package_lod2")
        include_collision = st.checkbox(
            "Collision Mesh", value=True, key="package_collision"
        )

    with col2:
        st.markdown("**Metadata**")
        include_manifest = st.checkbox(
            "Manifest JSON", value=True, key="package_manifest"
        )
        include_report = st.checkbox(
            "Quality Report", value=True, key="package_report"
        )
        include_preview = st.checkbox(
            "Preview Images", value=True, key="package_preview"
        )

        st.markdown("**Additional**")
        include_source = st.checkbox(
            "Source Files",
            value=False,
            help="Include original frames and masks",
            key="package_source",
        )

    st.divider()

    # Output path
    st.subheader("Output Location")

    output_dir = st.text_input(
        "Output Directory",
        value=config.config.output_dir,
        key="package_output_dir",
    )

    # Generate filename preview
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{selected_object.name}_{timestamp}"

    if export_format == "zip":
        filename += ".zip"

    st.text(f"Output: {output_dir}/{filename}")

    st.divider()

    # Get current session
    session: PackageSession | None = st.session_state.package_session

    # Progress section
    st.subheader("Packaging Progress")

    if session is not None and session.is_running:
        # Show progress
        st.progress(session.progress)
        st.text(f"Stage: {session.stage_display_name}")

        # Processing steps with status
        _render_stage_steps(session)

    elif session is not None and session.is_complete:
        st.success("Package created successfully!")

        # Show results
        _render_results(session)

    else:
        st.info("Click 'Create Package' to begin")

    st.divider()

    # Control buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Back to Optimize", use_container_width=True):
            st.session_state.navigate_to = "optimize"
            st.rerun()

    with col2:
        if session is not None and session.is_running:
            if st.button(
                "Cancel",
                type="secondary",
                use_container_width=True,
                key="package_cancel",
            ):
                st.session_state.package_session = package_service.stop_session(session)
                st.rerun()
        else:
            is_complete = session is not None and session.is_complete
            if st.button(
                "Create Package",
                type="primary",
                use_container_width=True,
                disabled=is_complete,
                key="package_create",
            ):
                _run_packaging(
                    package_service,
                    selected_object,
                    export_format,
                    include_lod0,
                    include_lod1,
                    include_lod2,
                    include_collision,
                    include_manifest,
                    include_report,
                    include_preview,
                    include_source,
                    output_dir,
                )

    with col3:
        can_proceed = session is not None and session.can_proceed
        if st.button(
            "View Report",
            type="primary" if can_proceed else "secondary",
            use_container_width=True,
            disabled=not can_proceed,
            key="package_report_btn",
        ):
            st.session_state.navigate_to = "report"
            st.rerun()


def _render_stage_steps(session: PackageSession) -> None:
    """Render the stage steps with completion status."""
    stages = [
        (PackageStage.COLLECTING_ASSETS, "Collecting asset files"),
        (PackageStage.GENERATING_MANIFEST, "Generating manifest"),
        (PackageStage.CREATING_ARCHIVE, "Creating archive"),
    ]

    current_index = STAGE_ORDER.index(session.current_stage)

    for stage, step_name in stages:
        stage_index = STAGE_ORDER.index(stage)

        # Skip archive stage if output format is directory
        if (
            stage == PackageStage.CREATING_ARCHIVE
            and session.config.output_format == "directory"
        ):
            continue

        if stage_index < current_index:
            st.success(f":white_check_mark: {step_name}")
        elif stage == session.current_stage:
            st.info(f":hourglass_flowing_sand: {step_name}")
        else:
            st.text(f":black_circle: {step_name}")


def _render_results(session: PackageSession) -> None:
    """Render packaging results."""
    metrics = session.metrics

    # Package stats
    st.subheader("Package Statistics")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Files", str(metrics.files_count))
    with col2:
        total_mb = metrics.total_size_bytes / (1024 * 1024)
        st.metric("Total Size", f"{total_mb:.1f} MB")
    with col3:
        if metrics.compressed_size_bytes is not None:
            compressed_mb = metrics.compressed_size_bytes / (1024 * 1024)
            st.metric("Compressed", f"{compressed_mb:.1f} MB")
        else:
            st.metric("Compressed", "N/A")
    with col4:
        st.metric("Format", "GLB + PNG")

    # Output path
    st.markdown("**Output Location**")
    st.code(metrics.output_path)

    # Files included
    with st.expander("Files Included", expanded=False):
        for filename in metrics.files_included:
            st.text(f"  - {filename}")


def _run_packaging(
    service: PackageService,
    selected_object: object,
    output_format: str,
    include_lod0: bool,
    include_lod1: bool,
    include_lod2: bool,
    include_collision: bool,
    include_manifest: bool,
    include_report: bool,
    include_preview: bool,
    include_source: bool,
    output_dir: str,
) -> None:
    """Run the packaging process with progress updates."""
    # Build config
    pkg_config = PackageConfig(
        output_format=output_format,
        include_lod0=include_lod0,
        include_lod1=include_lod1,
        include_lod2=include_lod2,
        include_collision=include_collision,
        include_manifest=include_manifest,
        include_report=include_report,
        include_preview=include_preview,
        include_source=include_source,
        output_dir=output_dir,
    )

    # Start session
    session = service.start_session(
        object_id=selected_object.id,  # type: ignore
        object_name=selected_object.name,  # type: ignore
        config=pkg_config,
    )
    st.session_state.package_session = session

    # Run through stages with visual feedback
    with st.spinner("Creating package..."):
        # Advance from IDLE to first stage
        session = service.advance_stage(session)
        st.session_state.package_session = session

        # Process each stage
        while not session.is_complete:
            time.sleep(0.3)  # Simulate processing time
            session = service.advance_stage(session)
            st.session_state.package_session = session

    # Update object stage
    selected_object.current_stage = PipelineStage.PACKAGE  # type: ignore
    st.session_state.selected_object = selected_object

    st.rerun()


# Run the page when loaded directly by Streamlit
render_package()
