"""Optimize page - mesh optimization, LOD generation, and scaling."""

import time

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.optimize_session import (
    STAGE_ORDER,
    OptimizeSession,
    OptimizeStage,
)
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.optimize_service import OptimizeService


def render_optimize() -> None:
    """Render the optimize page."""
    st.title("Optimize")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry", key="optimize_go_registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Optimizing **{selected_object.display_name}**")

    # Initialize config and service
    config = get_config_manager()
    optimize_service = OptimizeService(config.projects_dir)

    # Initialize session state
    if "optimize_session" not in st.session_state:
        st.session_state.optimize_session = None

    # Get input information from reconstruct session
    reconstruct_session = st.session_state.get("reconstruct_session")
    if reconstruct_session is not None:
        input_vertices = reconstruct_session.metrics.num_vertices
        input_triangles = reconstruct_session.metrics.num_triangles
        input_mesh_path = reconstruct_session.output_mesh_path
    else:
        # Fallback values if no reconstruct session
        input_vertices = 45230
        input_triangles = 89412
        input_mesh_path = None

    # Input mesh summary
    st.subheader("Input Mesh")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Vertices", f"{input_vertices:,}")
    with col2:
        st.metric("Triangles", f"{input_triangles:,}")
    with col3:
        size_mb = (input_vertices * 50 + input_triangles * 20) / (1024 * 1024)
        st.metric("Est. Size", f"{size_mb:.1f} MB")
    with col4:
        st.metric("Texture", "2048x2048")

    st.divider()

    # Optimization settings
    st.subheader("Optimization Settings")

    # Scale calibration
    st.markdown("**Scale Calibration**")

    if selected_object.known_dimension_mm:
        col1, col2 = st.columns(2)
        with col1:
            st.text(
                f"Known dimension: {selected_object.known_dimension_mm} mm "
                f"({selected_object.dimension_type})"
            )
        with col2:
            measured_dim = st.number_input(
                "Measured Dimension (mm)",
                min_value=0.1,
                value=float(selected_object.known_dimension_mm * 0.95),  # Simulated
                help="Measured dimension from reconstructed mesh",
                key="optimize_measured_dim",
            )
            scale_factor = selected_object.known_dimension_mm / measured_dim
            st.text(f"Scale factor: {scale_factor:.4f}")
    else:
        st.info("No known dimension specified. Scale will not be calibrated.")

    st.divider()

    # LOD settings
    st.markdown("**LOD Generation**")

    default_preset = config.config.default_preset
    lod_limits = default_preset.lod_triangle_limits

    col1, col2, col3 = st.columns(3)
    with col1:
        lod0 = st.number_input(
            "LOD0 Triangles",
            min_value=1000,
            max_value=500000,
            value=lod_limits[0],
            help="Highest detail level",
            key="optimize_lod0",
        )
    with col2:
        lod1 = st.number_input(
            "LOD1 Triangles",
            min_value=100,
            max_value=100000,
            value=lod_limits[1],
            help="Medium detail level",
            key="optimize_lod1",
        )
    with col3:
        lod2 = st.number_input(
            "LOD2 Triangles",
            min_value=10,
            max_value=50000,
            value=lod_limits[2],
            help="Low detail level",
            key="optimize_lod2",
        )

    st.divider()

    # Output settings
    st.markdown("**Output Settings**")

    col1, col2 = st.columns(2)
    with col1:
        st.selectbox(
            "Coordinate System",
            ["Z-up", "Y-up"],
            index=0 if default_preset.coordinate_system == "Z-up" else 1,
            key="optimize_coord_system",
        )
        st.selectbox(
            "Units",
            ["meter", "millimeter"],
            index=0 if default_preset.units == "meter" else 1,
            key="optimize_units",
        )
    with col2:
        st.selectbox(
            "Texture Resolution",
            [512, 1024, 2048, 4096],
            index=[512, 1024, 2048, 4096].index(default_preset.texture_resolution),
            key="optimize_tex_res",
        )
        st.checkbox("Generate collision mesh", value=True, key="optimize_collision")

    with st.expander("Advanced Options", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Fill small holes", value=True, key="optimize_fill_holes")
            st.slider(
                "Hole size threshold (mm)", 0.1, 10.0, 2.0, key="optimize_hole_size"
            )
            st.checkbox(
                "Remove isolated components", value=True, key="optimize_remove_isolated"
            )
        with col2:
            st.checkbox("Smooth mesh", value=True, key="optimize_smooth")
            st.slider("Smoothing iterations", 1, 10, 3, key="optimize_smooth_iter")
            st.checkbox("Optimize UV layout", value=True, key="optimize_uv")

    st.divider()

    # Get current session
    session: OptimizeSession | None = st.session_state.optimize_session

    # Progress section
    st.subheader("Optimization Progress")

    if session is not None and session.is_running:
        # Show progress
        st.progress(session.progress)
        st.text(f"Stage: {session.stage_display_name}")

        # Processing steps with status
        _render_stage_steps(session)

    elif session is not None and session.is_complete:
        st.success("Optimization complete!")

        # Show results
        _render_results(session)

    else:
        st.info("Click 'Start Optimization' to begin")

    st.divider()

    # Control buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Back to Reconstruct", use_container_width=True):
            st.session_state.navigate_to = "reconstruct"
            st.rerun()

    with col2:
        if session is not None and session.is_running:
            if st.button(
                "Cancel", type="secondary", use_container_width=True, key="optimize_cancel"
            ):
                st.session_state.optimize_session = optimize_service.stop_session(
                    session
                )
                st.rerun()
        else:
            is_complete = session is not None and session.is_complete
            if st.button(
                "Start Optimization",
                type="primary",
                use_container_width=True,
                disabled=is_complete,
                key="optimize_start",
            ):
                _run_optimization(
                    optimize_service,
                    selected_object,
                    input_mesh_path,
                    input_vertices,
                    input_triangles,
                    lod0,
                    lod1,
                    lod2,
                )

    with col3:
        can_proceed = session is not None and session.can_proceed
        if st.button(
            "Proceed to Package",
            type="primary" if can_proceed else "secondary",
            use_container_width=True,
            disabled=not can_proceed,
            key="optimize_proceed",
        ):
            st.session_state.navigate_to = "package"
            st.rerun()


def _render_stage_steps(session: OptimizeSession) -> None:
    """Render the stage steps with completion status."""
    stages = [
        (OptimizeStage.SCALE_CALIBRATION, "Applying scale calibration"),
        (OptimizeStage.MESH_CLEANING, "Cleaning mesh (holes, components)"),
        (OptimizeStage.LOD_GENERATION, "Generating LOD levels"),
        (OptimizeStage.TEXTURE_OPTIMIZATION, "Optimizing textures"),
        (OptimizeStage.COLLISION_MESH, "Creating collision mesh"),
    ]

    current_index = STAGE_ORDER.index(session.current_stage)

    for stage, step_name in stages:
        stage_index = STAGE_ORDER.index(stage)

        if stage_index < current_index:
            st.success(f":white_check_mark: {step_name}")
        elif stage == session.current_stage:
            st.info(f":hourglass_flowing_sand: {step_name}")
        else:
            st.text(f":black_circle: {step_name}")


def _render_results(session: OptimizeSession) -> None:
    """Render optimization results."""
    metrics = session.metrics

    # LOD comparison
    st.subheader("LOD Levels")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**LOD0** (High)")
        st.text(f"Triangles: {metrics.lod0_triangles:,}")
        lod0_size = metrics.lod0_triangles * 50 / (1024 * 1024)
        st.text(f"Size: {lod0_size:.1f} MB")
        st.markdown(
            '<div style="background: #2d5a27; height: 120px; border-radius: 4px; '
            'display: flex; align-items: center; justify-content: center; color: white;">'
            "High Detail</div>",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("**LOD1** (Medium)")
        st.text(f"Triangles: {metrics.lod1_triangles:,}")
        lod1_size = metrics.lod1_triangles * 50 / (1024 * 1024)
        st.text(f"Size: {lod1_size:.1f} MB")
        st.markdown(
            '<div style="background: #5a5a27; height: 120px; border-radius: 4px; '
            'display: flex; align-items: center; justify-content: center; color: white;">'
            "Medium Detail</div>",
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown("**LOD2** (Low)")
        st.text(f"Triangles: {metrics.lod2_triangles:,}")
        lod2_size = metrics.lod2_triangles * 50 / (1024 * 1024)
        st.text(f"Size: {lod2_size:.1f} MB")
        st.markdown(
            '<div style="background: #5a2727; height: 120px; border-radius: 4px; '
            'display: flex; align-items: center; justify-content: center; color: white;">'
            "Low Detail</div>",
            unsafe_allow_html=True,
        )

    # Quality metrics
    st.subheader("Quality Metrics")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Mesh Processing**")
        st.text(f"Holes filled: {metrics.holes_filled}")
        st.text(f"Components removed: {metrics.components_removed}")
        st.text(f"Scale applied: {metrics.scale_factor:.4f}")
    with col2:
        st.markdown("**Output**")
        st.text("UV overlap: 0%")
        st.text(f"Collision mesh: {metrics.collision_triangles} triangles")
        bx, by, bz = metrics.bounding_box
        st.text(f"Bounding box: {bx:.2f} x {by:.2f} x {bz:.2f} m")


def _run_optimization(
    service: OptimizeService,
    selected_object: object,
    input_mesh_path: str | None,
    input_vertices: int,
    input_triangles: int,
    lod0_target: int,
    lod1_target: int,
    lod2_target: int,
) -> None:
    """Run the optimization process with progress updates."""
    # Start session
    session = service.start_session(
        object_id=selected_object.id,  # type: ignore
        input_mesh_path=input_mesh_path,
        input_vertices=input_vertices,
        input_triangles=input_triangles,
        lod0_target=lod0_target,
        lod1_target=lod1_target,
        lod2_target=lod2_target,
    )
    st.session_state.optimize_session = session

    # Run through stages with visual feedback
    with st.spinner("Optimizing..."):
        # Advance from IDLE to first stage
        session = service.advance_stage(session)
        st.session_state.optimize_session = session

        # Process each stage
        while not session.is_complete:
            time.sleep(0.3)  # Simulate processing time
            session = service.advance_stage(session)
            st.session_state.optimize_session = session

    # Update object stage
    selected_object.current_stage = PipelineStage.OPTIMIZE  # type: ignore
    st.session_state.selected_object = selected_object

    st.rerun()


# Run the page when loaded directly by Streamlit
render_optimize()
