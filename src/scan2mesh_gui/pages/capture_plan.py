"""Capture Plan page - plan scanning coverage."""

from pathlib import Path

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.capture_plan import CapturePlanPreset
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.capture_plan_service import CapturePlanService
from scan2mesh_gui.services.pipeline_service import PipelineService


def render_capture_plan() -> None:
    """Render the capture plan page."""
    st.title("Capture Plan")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry", key="capture_plan_go_registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Planning capture for **{selected_object.display_name}**")

    config = get_config_manager()
    pipeline = PipelineService(config.projects_dir)
    capture_service = CapturePlanService(config.projects_dir)

    # Object info card
    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Object Information**")
            st.text(f"Name: {selected_object.name}")
            st.text(f"Display Name: {selected_object.display_name}")
            st.text(f"Class ID: {selected_object.class_id}")

            if selected_object.known_dimension_mm:
                st.text(
                    f"Known Dimension: {selected_object.known_dimension_mm} mm "
                    f"({selected_object.dimension_type})"
                )

        with col2:
            st.markdown("**Status**")
            st.text(f"Current Stage: {selected_object.current_stage.value.capitalize()}")
            st.text(f"Quality Status: {selected_object.quality_status.value.upper()}")

    st.divider()

    # Capture preset selection
    st.subheader("Capture Preset")

    # Map preset names to enum values
    preset_options = [
        CapturePlanPreset.STANDARD,
        CapturePlanPreset.HIGH_QUALITY,
        CapturePlanPreset.QUICK,
    ]

    def format_preset(p: CapturePlanPreset) -> str:
        info = capture_service.get_preset_info(p)
        return {
            CapturePlanPreset.STANDARD: f"Standard ({info['keyframes']} keyframes, balanced)",
            CapturePlanPreset.HIGH_QUALITY: f"High Quality ({info['keyframes']} keyframes, detailed)",
            CapturePlanPreset.QUICK: f"Quick ({info['keyframes']} keyframes, fast)",
        }.get(p, p.value)

    selected_preset = st.selectbox(
        "Select Preset",
        preset_options,
        format_func=format_preset,
    )

    # Get preset info from service
    preset_info = capture_service.get_preset_info(selected_preset)

    # Preset descriptions
    preset_descriptions = {
        CapturePlanPreset.STANDARD: (
            f"Balanced coverage with {preset_info['elevation_levels']} elevation levels "
            f"x {preset_info['azimuth_positions']} azimuth positions"
        ),
        CapturePlanPreset.HIGH_QUALITY: (
            f"Detailed coverage with {preset_info['elevation_levels']} elevation levels "
            f"x {preset_info['azimuth_positions']} azimuth positions"
        ),
        CapturePlanPreset.QUICK: (
            f"Fast capture with {preset_info['elevation_levels']} elevation levels "
            f"x {preset_info['azimuth_positions']} azimuth positions"
        ),
    }

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Target Keyframes", preset_info["keyframes"])
    with col2:
        st.metric("Est. Time", preset_info["time_estimate"])
    with col3:
        st.metric("Coverage", "360°")

    st.caption(preset_descriptions.get(selected_preset, ""))

    st.divider()

    # Coverage visualization
    st.subheader("Coverage Plan")

    # Display spherical coverage visualization (placeholder)
    st.markdown("**Spherical Coverage Map**")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
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
        """
        )
        st.caption("● = Object center, ○ = Camera positions")

    with col2:
        st.markdown("**Elevation Levels**")
        elevations = CapturePlanService.get_elevation_angles(selected_preset)
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
                value=preset_info["azimuth_positions"],
                help="Number of positions around the object",
                disabled=True,  # Read-only for now
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
                value=preset_info["elevation_levels"],
                help="Number of vertical levels",
                disabled=True,  # Read-only for now
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

            # Generate capture plan using CapturePlanService
            with st.spinner("Generating capture plan..."):
                plan = capture_service.generate_plan(
                    preset=selected_preset,
                    object_id=selected_object.id,
                )

                # Save to session state (as dict for compatibility)
                st.session_state.capture_plan = {
                    "preset": plan.preset.value,
                    "viewpoints": plan.num_viewpoints,
                    "target_keyframes": plan.num_viewpoints,
                    "min_required_frames": plan.min_required_frames,
                    "recommended_distance_m": plan.recommended_distance_m,
                    "notes": plan.notes,
                }

                # Save to project directory
                if selected_object.project_path:
                    capture_service.save_plan(
                        plan, Path(selected_object.project_path)
                    )

            # Update stage
            selected_object.current_stage = PipelineStage.PLAN
            st.session_state.selected_object = selected_object

            st.success("Capture plan generated!")
            st.session_state.navigate_to = "capture"
            st.rerun()
