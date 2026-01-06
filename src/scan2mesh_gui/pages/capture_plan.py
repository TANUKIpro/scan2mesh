"""Capture Plan page - plan scanning coverage."""

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.pipeline_service import PipelineService


def render_capture_plan() -> None:
    """Render the capture plan page."""
    st.title("Capture Plan")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Planning capture for **{selected_object.display_name}**")

    config = get_config_manager()
    pipeline = PipelineService(config.projects_dir)

    # Object info card
    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Object Information**")
            st.text(f"Name: {selected_object.name}")
            st.text(f"Display Name: {selected_object.display_name}")
            st.text(f"Class ID: {selected_object.class_id}")

            if selected_object.known_dimension_mm:
                st.text(f"Known Dimension: {selected_object.known_dimension_mm} mm ({selected_object.dimension_type})")

        with col2:
            st.markdown("**Status**")
            st.text(f"Current Stage: {selected_object.current_stage.value.capitalize()}")
            st.text(f"Quality Status: {selected_object.quality_status.value.upper()}")

    st.divider()

    # Capture preset selection
    st.subheader("Capture Preset")

    preset = st.selectbox(
        "Select Preset",
        ["standard", "high_quality", "quick"],
        format_func=lambda x: {
            "standard": "Standard (36 keyframes, balanced)",
            "high_quality": "High Quality (72 keyframes, detailed)",
            "quick": "Quick (18 keyframes, fast)",
        }.get(x, x),
    )

    # Preset details
    preset_info = {
        "standard": {
            "keyframes": 36,
            "description": "Balanced coverage with 6 elevation levels x 6 azimuth positions",
            "time_estimate": "3-5 minutes",
        },
        "high_quality": {
            "keyframes": 72,
            "description": "Detailed coverage with 12 elevation levels x 6 azimuth positions",
            "time_estimate": "6-10 minutes",
        },
        "quick": {
            "keyframes": 18,
            "description": "Fast capture with 3 elevation levels x 6 azimuth positions",
            "time_estimate": "1-2 minutes",
        },
    }

    info = preset_info[preset]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Target Keyframes", info["keyframes"])
    with col2:
        st.metric("Est. Time", info["time_estimate"])
    with col3:
        st.metric("Coverage", "360°")

    st.caption(info["description"])

    st.divider()

    # Coverage visualization
    st.subheader("Coverage Plan")

    # Display spherical coverage visualization (placeholder)
    st.markdown("**Spherical Coverage Map**")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ```
              TOP (6 shots)
                  ○ ○ ○
                 ○     ○
                ○       ○

        SIDE   ○   ●   ○   SIDE
        (6)    ○       ○   (6)
                ○     ○
                  ○ ○ ○
             BOTTOM (6 shots)
        ```
        """)
        st.caption("● = Object center, ○ = Camera positions")

    with col2:
        st.markdown("**Elevation Levels**")
        if preset == "standard":
            elevations = [0, 30, 60, 90, 120, 150]
        elif preset == "high_quality":
            elevations = [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165]
        else:
            elevations = [0, 60, 120]

        for elev in elevations:
            st.text(f"• {elev}° elevation")

    st.divider()

    # Advanced settings
    with st.expander("Advanced Settings", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.number_input(
                "Azimuth Positions",
                min_value=4,
                max_value=12,
                value=6,
                help="Number of positions around the object",
            )

            st.number_input(
                "Min Frame Interval (ms)",
                min_value=100,
                max_value=1000,
                value=200,
                help="Minimum time between frames",
            )

        with col2:
            st.number_input(
                "Elevation Levels",
                min_value=2,
                max_value=12,
                value=6 if preset == "standard" else (12 if preset == "high_quality" else 3),
                help="Number of vertical levels",
            )

            st.slider(
                "Quality Threshold",
                min_value=0.5,
                max_value=1.0,
                value=0.7,
                help="Minimum quality score to accept frame",
            )

    st.divider()

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Back to Registry", use_container_width=True):
            st.session_state.navigate_to = "registry"
            st.rerun()

    with col2:
        pass  # Spacer

    with col3:
        if st.button("Start Capture", type="primary", use_container_width=True):
            # Initialize project if needed
            if not selected_object.project_path:
                with st.spinner("Initializing project..."):
                    project_path = pipeline.init_project(selected_object)
                    selected_object.project_path = str(project_path)

            # Generate capture plan
            with st.spinner("Generating capture plan..."):
                plan = pipeline.generate_plan(
                    selected_object.project_path,
                    preset=preset,
                )
                st.session_state.capture_plan = plan

            # Update stage
            selected_object.current_stage = PipelineStage.PLAN
            st.session_state.selected_object = selected_object

            st.success("Capture plan generated!")
            st.session_state.navigate_to = "capture"
            st.rerun()


# Run the page when loaded directly by Streamlit
render_capture_plan()
