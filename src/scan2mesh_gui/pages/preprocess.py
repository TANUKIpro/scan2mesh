"""Preprocess page - background removal and mask generation."""

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.pipeline_service import PipelineService


def render_preprocess() -> None:
    """Render the preprocess page."""
    st.title("Preprocess")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Preprocessing **{selected_object.display_name}**")

    config = get_config_manager()
    pipeline = PipelineService(config.projects_dir)

    # Initialize state
    if "preprocess_progress" not in st.session_state:
        st.session_state.preprocess_progress = 0.0
    if "preprocess_running" not in st.session_state:
        st.session_state.preprocess_running = False
    if "preprocess_complete" not in st.session_state:
        st.session_state.preprocess_complete = False

    # Capture summary
    st.subheader("Capture Summary")

    captured_frames = st.session_state.get("captured_frames", 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Captured Frames", captured_frames)
    with col2:
        st.metric("Valid Frames", int(captured_frames * 0.9))
    with col3:
        st.metric("Estimated Time", f"{captured_frames * 2}s")

    st.divider()

    # Processing method selection
    st.subheader("Processing Method")

    method = st.selectbox(
        "Background Removal Method",
        ["depth_threshold", "grabcut", "u2net"],
        format_func=lambda x: {
            "depth_threshold": "Depth Threshold (Fast, requires clean background)",
            "grabcut": "GrabCut (Medium, semi-automatic)",
            "u2net": "U2-Net (Slow, AI-powered, best quality)",
        }.get(x, x),
    )

    # Method-specific settings
    if method == "depth_threshold":
        with st.expander("Depth Threshold Settings", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.slider(
                    "Min Depth (mm)",
                    min_value=100,
                    max_value=2000,
                    value=300,
                    help="Minimum depth to include",
                )
            with col2:
                st.slider(
                    "Max Depth (mm)",
                    min_value=500,
                    max_value=5000,
                    value=1500,
                    help="Maximum depth to include",
                )

    elif method == "grabcut":
        with st.expander("GrabCut Settings", expanded=True):
            st.number_input(
                "Iterations",
                min_value=1,
                max_value=10,
                value=5,
                help="Number of GrabCut iterations",
            )
            st.checkbox("Auto-detect ROI", value=True)

    else:  # u2net
        with st.expander("U2-Net Settings", expanded=True):
            st.selectbox(
                "Model Size",
                ["small", "full"],
                format_func=lambda x: {
                    "small": "Small (Faster, lower quality)",
                    "full": "Full (Slower, higher quality)",
                }.get(x, x),
            )
            st.slider(
                "Threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.5,
                help="Mask threshold",
            )

    st.divider()

    # Progress section
    st.subheader("Processing Progress")

    if st.session_state.preprocess_running:
        progress = st.session_state.preprocess_progress
        st.progress(progress)
        st.text(f"Processing frame {int(progress * captured_frames)} / {captured_frames}")

        # Processing steps
        steps = [
            ("Loading frames", progress > 0.1),
            ("Generating masks", progress > 0.3),
            ("Refining edges", progress > 0.6),
            ("Validating output", progress > 0.9),
        ]

        for step_name, completed in steps:
            if completed:
                st.success(f":white_check_mark: {step_name}")
            else:
                st.info(f":hourglass_flowing_sand: {step_name}")

    elif st.session_state.preprocess_complete:
        st.success("Preprocessing complete!")

        # Show results
        st.subheader("Results")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Processed Frames", captured_frames)
        with col2:
            st.metric("Valid Masks", int(captured_frames * 0.95))
        with col3:
            st.metric("Mask Quality", "92%")

        # Sample preview
        st.markdown("**Sample Output**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                '<div style="background: #333; height: 150px; display: flex; align-items: center; justify-content: center; color: #888;">Original</div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                '<div style="background: #444; height: 150px; display: flex; align-items: center; justify-content: center; color: #888;">Mask</div>',
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                '<div style="background: #555; height: 150px; display: flex; align-items: center; justify-content: center; color: #888;">Masked</div>',
                unsafe_allow_html=True,
            )

    else:
        st.info("Click 'Start Preprocessing' to begin")

    st.divider()

    # Control buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Back to Capture", use_container_width=True):
            st.session_state.navigate_to = "capture"
            st.rerun()

    with col2:
        if st.session_state.preprocess_running:
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state.preprocess_running = False
                st.session_state.preprocess_progress = 0.0
                st.rerun()
        else:
            if st.button(
                "Start Preprocessing",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.preprocess_complete,
            ):
                st.session_state.preprocess_running = True
                st.session_state.preprocess_progress = 0.0

                # Simulate preprocessing (in real app, this would run async)
                with st.spinner("Processing..."):
                    # Simulate progress
                    import time
                    for i in range(10):
                        st.session_state.preprocess_progress = (i + 1) / 10
                        time.sleep(0.2)

                st.session_state.preprocess_running = False
                st.session_state.preprocess_complete = True

                # Update object stage
                selected_object.current_stage = PipelineStage.PREPROCESS
                st.session_state.selected_object = selected_object

                st.rerun()

    with col3:
        if st.button(
            "Proceed to Reconstruct",
            type="primary" if st.session_state.preprocess_complete else "secondary",
            use_container_width=True,
            disabled=not st.session_state.preprocess_complete,
        ):
            st.session_state.navigate_to = "reconstruct"
            st.rerun()


# Run the page when loaded directly by Streamlit
render_preprocess()
