"""Optimize page - mesh optimization, LOD generation, and scaling."""

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.pipeline_service import PipelineService


def render_optimize() -> None:
    """Render the optimize page."""
    st.title("Optimize")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Optimizing **{selected_object.display_name}**")

    config = get_config_manager()
    pipeline = PipelineService(config.projects_dir)

    # Initialize state
    if "optimize_progress" not in st.session_state:
        st.session_state.optimize_progress = 0.0
    if "optimize_running" not in st.session_state:
        st.session_state.optimize_running = False
    if "optimize_complete" not in st.session_state:
        st.session_state.optimize_complete = False

    # Input mesh summary
    st.subheader("Input Mesh")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Vertices", "45,230")
    with col2:
        st.metric("Triangles", "89,412")
    with col3:
        st.metric("File Size", "12.4 MB")
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
            st.text(f"Known dimension: {selected_object.known_dimension_mm} mm ({selected_object.dimension_type})")
        with col2:
            measured_dim = st.number_input(
                "Measured Dimension (mm)",
                min_value=0.1,
                value=selected_object.known_dimension_mm * 0.95,  # Simulated
                help="Measured dimension from reconstructed mesh",
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
        )
    with col2:
        lod1 = st.number_input(
            "LOD1 Triangles",
            min_value=100,
            max_value=100000,
            value=lod_limits[1],
            help="Medium detail level",
        )
    with col3:
        lod2 = st.number_input(
            "LOD2 Triangles",
            min_value=10,
            max_value=50000,
            value=lod_limits[2],
            help="Low detail level",
        )

    st.divider()

    # Output settings
    st.markdown("**Output Settings**")

    col1, col2 = st.columns(2)
    with col1:
        coordinate_system = st.selectbox(
            "Coordinate System",
            ["Z-up", "Y-up"],
            index=0 if default_preset.coordinate_system == "Z-up" else 1,
        )
        units = st.selectbox(
            "Units",
            ["meter", "millimeter"],
            index=0 if default_preset.units == "meter" else 1,
        )
    with col2:
        texture_resolution = st.selectbox(
            "Texture Resolution",
            [512, 1024, 2048, 4096],
            index=[512, 1024, 2048, 4096].index(default_preset.texture_resolution),
        )
        st.checkbox("Generate collision mesh", value=True)

    with st.expander("Advanced Options", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Fill small holes", value=True)
            st.slider("Hole size threshold (mm)", 0.1, 10.0, 2.0)
            st.checkbox("Remove isolated components", value=True)
        with col2:
            st.checkbox("Smooth mesh", value=True)
            st.slider("Smoothing iterations", 1, 10, 3)
            st.checkbox("Optimize UV layout", value=True)

    st.divider()

    # Progress section
    st.subheader("Optimization Progress")

    if st.session_state.optimize_running:
        progress = st.session_state.optimize_progress
        st.progress(progress)

        steps = [
            ("Applying scale", progress > 0.1),
            ("Cleaning mesh", progress > 0.2),
            ("Generating LOD0", progress > 0.4),
            ("Generating LOD1", progress > 0.6),
            ("Generating LOD2", progress > 0.75),
            ("Creating collision mesh", progress > 0.85),
            ("Optimizing textures", progress > 0.95),
        ]

        for step_name, completed in steps:
            if completed:
                st.success(f":white_check_mark: {step_name}")
            else:
                st.text(f":black_circle: {step_name}")

    elif st.session_state.optimize_complete:
        st.success("Optimization complete!")

        # Show results
        st.subheader("Results")

        # LOD comparison
        st.markdown("**LOD Levels**")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**LOD0** (High)")
            st.text(f"Triangles: {min(lod0, 89412)}")
            st.text(f"Size: {min(lod0, 89412) * 0.0001:.1f} MB")
            st.markdown(
                '<div style="background: #2d5a27; height: 120px; border-radius: 4px; display: flex; align-items: center; justify-content: center;">High Detail</div>',
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown("**LOD1** (Medium)")
            st.text(f"Triangles: {lod1}")
            st.text(f"Size: {lod1 * 0.0001:.1f} MB")
            st.markdown(
                '<div style="background: #5a5a27; height: 120px; border-radius: 4px; display: flex; align-items: center; justify-content: center;">Medium Detail</div>',
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown("**LOD2** (Low)")
            st.text(f"Triangles: {lod2}")
            st.text(f"Size: {lod2 * 0.0001:.1f} MB")
            st.markdown(
                '<div style="background: #5a2727; height: 120px; border-radius: 4px; display: flex; align-items: center; justify-content: center;">Low Detail</div>',
                unsafe_allow_html=True,
            )

        # Quality metrics
        st.markdown("**Quality Metrics**")

        col1, col2 = st.columns(2)
        with col1:
            st.text("Holes filled: 2")
            st.text("Components removed: 1")
            st.text("Scale applied: 1.0523")
        with col2:
            st.text("UV overlap: 0%")
            st.text("Collision mesh: 512 triangles")
            st.text("Bounding box: 0.22 x 0.22 x 0.22 m")

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
        if st.session_state.optimize_running:
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state.optimize_running = False
                st.session_state.optimize_progress = 0.0
                st.rerun()
        else:
            if st.button(
                "Start Optimization",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.optimize_complete,
            ):
                st.session_state.optimize_running = True
                st.session_state.optimize_progress = 0.0

                # Simulate optimization
                import time
                with st.spinner("Optimizing..."):
                    for i in range(10):
                        st.session_state.optimize_progress = (i + 1) / 10
                        time.sleep(0.3)

                st.session_state.optimize_running = False
                st.session_state.optimize_complete = True

                # Update object stage
                selected_object.current_stage = PipelineStage.OPTIMIZE
                st.session_state.selected_object = selected_object

                st.rerun()

    with col3:
        if st.button(
            "Proceed to Package",
            type="primary" if st.session_state.optimize_complete else "secondary",
            use_container_width=True,
            disabled=not st.session_state.optimize_complete,
        ):
            st.session_state.navigate_to = "package"
            st.rerun()


# Run the page when loaded directly by Streamlit
render_optimize()
