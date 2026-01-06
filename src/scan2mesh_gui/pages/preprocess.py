"""Preprocess page - background removal and mask generation."""

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.capture_session import CaptureSession
from scan2mesh_gui.models.preprocess_session import MaskMethod, PreprocessSession
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.preprocess_service import PreprocessService


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

    # Get capture session
    capture_session = st.session_state.get("capture_session")

    # Initialize services
    config = get_config_manager()
    preprocess_service = PreprocessService(config.projects_dir)

    # Get captured frame count
    if capture_session and isinstance(capture_session, CaptureSession):
        captured_frames = capture_session.frames
        captured_frame_count = len(captured_frames)
    else:
        captured_frames = []
        captured_frame_count = 0

    # Capture summary
    st.subheader("Capture Summary")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Captured Frames", captured_frame_count)
    with col2:
        valid_frames = sum(
            1 for f in captured_frames if f.quality.is_keyframe
        ) if captured_frames else 0
        st.metric("Valid Frames", valid_frames)
    with col3:
        estimated_time = max(1, captured_frame_count * 2)
        st.metric("Estimated Time", f"{estimated_time}s")

    if captured_frame_count == 0:
        st.warning("No captured frames found. Please complete the capture step first.")
        if st.button("Go to Capture"):
            st.session_state.navigate_to = "capture"
            st.rerun()
        return

    st.divider()

    # Processing method selection
    st.subheader("Processing Method")

    method_key = st.selectbox(
        "Background Removal Method",
        ["depth_threshold", "grabcut", "u2net"],
        format_func=lambda x: {
            "depth_threshold": "Depth Threshold (Fast, requires clean background)",
            "grabcut": "GrabCut (Medium, semi-automatic)",
            "u2net": "U2-Net (Slow, AI-powered, best quality)",
        }.get(x, x),
        key="preprocess_method",
    )

    # Convert to enum
    method = MaskMethod(method_key)

    # Method-specific settings
    settings: dict[str, float] = {}

    if method == MaskMethod.DEPTH_THRESHOLD:
        with st.expander("Depth Threshold Settings", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                min_depth = st.slider(
                    "Min Depth (mm)",
                    min_value=100,
                    max_value=2000,
                    value=300,
                    help="Minimum depth to include",
                    key="min_depth",
                )
                settings["min_depth"] = float(min_depth)
            with col2:
                max_depth = st.slider(
                    "Max Depth (mm)",
                    min_value=500,
                    max_value=5000,
                    value=1500,
                    help="Maximum depth to include",
                    key="max_depth",
                )
                settings["max_depth"] = float(max_depth)

    elif method == MaskMethod.GRABCUT:
        with st.expander("GrabCut Settings", expanded=True):
            iterations = st.number_input(
                "Iterations",
                min_value=1,
                max_value=10,
                value=5,
                help="Number of GrabCut iterations",
                key="grabcut_iterations",
            )
            settings["iterations"] = float(iterations)
            st.checkbox("Auto-detect ROI", value=True, key="grabcut_auto_roi")

    else:  # u2net
        with st.expander("U2-Net Settings", expanded=True):
            st.selectbox(
                "Model Size",
                ["small", "full"],
                format_func=lambda x: {
                    "small": "Small (Faster, lower quality)",
                    "full": "Full (Slower, higher quality)",
                }.get(x, x),
                key="u2net_model_size",
            )
            threshold = st.slider(
                "Threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.5,
                help="Mask threshold",
                key="u2net_threshold",
            )
            settings["threshold"] = threshold

    st.divider()

    # Initialize or get preprocess session
    preprocess_session = st.session_state.get("preprocess_session")

    # Progress section
    st.subheader("Processing Progress")

    if preprocess_session and isinstance(preprocess_session, PreprocessSession):
        is_running = preprocess_session.is_running
        is_complete = preprocess_session.is_complete
        progress = preprocess_session.progress
        metrics = preprocess_session.metrics
        masked_frames = preprocess_session.masked_frames
    else:
        is_running = False
        is_complete = False
        progress = 0.0
        metrics = None
        masked_frames = []

    if is_running:
        st.progress(progress)
        processed_count = len(masked_frames)
        st.text(f"Processing frame {processed_count} / {captured_frame_count}")

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

    elif is_complete:
        st.success("Preprocessing complete!")

        # Show results
        st.subheader("Results")

        if metrics:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Processed Frames", metrics.num_processed)
            with col2:
                st.metric("Valid Masks", metrics.num_valid)
            with col3:
                st.metric("Mask Area", f"{metrics.mask_area_ratio_mean:.0%}")
            with col4:
                st.metric("Edge Quality", f"{metrics.edge_quality_mean:.0%}")

        # Before/After preview
        st.markdown("**Sample Output**")

        if masked_frames:
            # Show last processed frame
            last_frame = masked_frames[-1]
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Original**")
                # Find original frame
                original_frame = next(
                    (f for f in captured_frames if f.frame_id == last_frame.frame_id),
                    None
                )
                if original_frame and original_frame.rgb_path:
                    try:
                        import cv2
                        img = cv2.imread(original_frame.rgb_path)
                        if img is not None:
                            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            st.image(img_rgb, use_container_width=True)
                        else:
                            st.markdown(
                                '<div style="background: #333; height: 150px; display: flex; '
                                'align-items: center; justify-content: center; color: #888;">'
                                "Original</div>",
                                unsafe_allow_html=True,
                            )
                    except Exception:
                        st.markdown(
                            '<div style="background: #333; height: 150px; display: flex; '
                            'align-items: center; justify-content: center; color: #888;">'
                            "Original</div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        '<div style="background: #333; height: 150px; display: flex; '
                        'align-items: center; justify-content: center; color: #888;">'
                        "Original</div>",
                        unsafe_allow_html=True,
                    )

            with col2:
                st.markdown("**Mask**")
                if last_frame.mask_path:
                    try:
                        import cv2
                        mask_img = cv2.imread(last_frame.mask_path, cv2.IMREAD_GRAYSCALE)
                        if mask_img is not None:
                            st.image(mask_img, use_container_width=True)
                        else:
                            st.markdown(
                                '<div style="background: #444; height: 150px; display: flex; '
                                'align-items: center; justify-content: center; color: #888;">'
                                "Mask</div>",
                                unsafe_allow_html=True,
                            )
                    except Exception:
                        st.markdown(
                            '<div style="background: #444; height: 150px; display: flex; '
                            'align-items: center; justify-content: center; color: #888;">'
                            "Mask</div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        '<div style="background: #444; height: 150px; display: flex; '
                        'align-items: center; justify-content: center; color: #888;">'
                        "Mask</div>",
                        unsafe_allow_html=True,
                    )

            with col3:
                st.markdown("**Masked**")
                if last_frame.rgb_masked_path:
                    try:
                        import cv2
                        masked_img = cv2.imread(last_frame.rgb_masked_path)
                        if masked_img is not None:
                            masked_rgb = cv2.cvtColor(masked_img, cv2.COLOR_BGR2RGB)
                            st.image(masked_rgb, use_container_width=True)
                        else:
                            st.markdown(
                                '<div style="background: #555; height: 150px; display: flex; '
                                'align-items: center; justify-content: center; color: #888;">'
                                "Masked</div>",
                                unsafe_allow_html=True,
                            )
                    except Exception:
                        st.markdown(
                            '<div style="background: #555; height: 150px; display: flex; '
                            'align-items: center; justify-content: center; color: #888;">'
                            "Masked</div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        '<div style="background: #555; height: 150px; display: flex; '
                        'align-items: center; justify-content: center; color: #888;">'
                        "Masked</div>",
                        unsafe_allow_html=True,
                    )
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    '<div style="background: #333; height: 150px; display: flex; '
                    'align-items: center; justify-content: center; color: #888;">'
                    "Original</div>",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    '<div style="background: #444; height: 150px; display: flex; '
                    'align-items: center; justify-content: center; color: #888;">'
                    "Mask</div>",
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    '<div style="background: #555; height: 150px; display: flex; '
                    'align-items: center; justify-content: center; color: #888;">'
                    "Masked</div>",
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
        if is_running:
            if st.button("Cancel", type="secondary", use_container_width=True):
                if preprocess_session:
                    stopped_session = preprocess_service.stop_session(preprocess_session)
                    st.session_state.preprocess_session = stopped_session
                st.rerun()
        else:
            if st.button(
                "Start Preprocessing",
                type="primary",
                use_container_width=True,
                disabled=is_complete or captured_frame_count == 0,
            ):
                # Start a new preprocessing session
                new_session = preprocess_service.start_session(
                    object_id=selected_object.id,
                    captured_frames=captured_frames,
                )
                st.session_state.preprocess_session = new_session

                # Process all frames
                with st.spinner("Processing frames..."):
                    import time
                    for frame in captured_frames:
                        result = preprocess_service.process_frame(
                            new_session,
                            frame,
                            method,
                            settings,
                        )
                        if result:
                            masked_frame, rgb_masked, depth_masked, mask = result

                            # Save the masked frame
                            saved_frame = preprocess_service.save_masked_frame(
                                new_session,
                                masked_frame,
                                rgb_masked,
                                depth_masked,
                                mask,
                            )

                            # Add to session
                            new_session = preprocess_service.add_masked_frame_to_session(
                                new_session, saved_frame
                            )
                            st.session_state.preprocess_session = new_session

                        # Small delay for visual feedback
                        time.sleep(0.1)

                # Stop the session
                stopped_session = preprocess_service.stop_session(new_session)
                st.session_state.preprocess_session = stopped_session

                # Update object stage
                selected_object.current_stage = PipelineStage.PREPROCESS
                st.session_state.selected_object = selected_object

                st.rerun()

    with col3:
        if st.button(
            "Proceed to Reconstruct",
            type="primary" if is_complete else "secondary",
            use_container_width=True,
            disabled=not is_complete,
        ):
            st.session_state.navigate_to = "reconstruct"
            st.rerun()
