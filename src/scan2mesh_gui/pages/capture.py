"""Capture page - real-time RGB-D capture with quality monitoring."""

import streamlit as st

from scan2mesh_gui.components.camera_preview import render_camera_preview
from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.capture_plan import CapturePlan
from scan2mesh_gui.models.capture_session import CaptureSession
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.capture_service import CaptureService
from scan2mesh_gui.services.device_service import DeviceService


def render_capture() -> None:
    """Render the capture page."""
    st.title("Capture")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Capturing **{selected_object.display_name}**")

    # Check for capture plan
    capture_plan = st.session_state.get("capture_plan")
    if capture_plan is None:
        st.warning("Please generate a capture plan first")
        if st.button("Go to Capture Plan"):
            st.session_state.navigate_to = "capture_plan"
            st.rerun()
        return

    # Get target keyframes from capture plan
    if isinstance(capture_plan, CapturePlan):
        target_keyframes = capture_plan.min_required_frames
    elif isinstance(capture_plan, dict):
        target_keyframes = capture_plan.get("target_keyframes", 36)
    else:
        target_keyframes = 36

    # Check for camera connection
    device_service = DeviceService()
    devices = device_service.list_devices()

    if not devices:
        st.error("No RealSense camera detected")
        if st.button("Go to Devices"):
            st.session_state.navigate_to = "devices"
            st.rerun()
        return

    # Initialize services
    config = get_config_manager()
    capture_service = CaptureService(config.projects_dir)

    # Initialize or get capture session
    session = st.session_state.get("capture_session")

    # Camera preview section
    st.subheader("Camera Preview")

    # Get current frame for preview
    current_frame = st.session_state.get("current_frame")
    if current_frame:
        rgb, depth = current_frame
        render_camera_preview(rgb, depth)
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.info("RGB Preview")
            st.markdown(
                '<div style="background: #1a1a1a; height: 200px; display: flex; '
                'align-items: center; justify-content: center; color: #666;">'
                "Camera feed will appear here</div>",
                unsafe_allow_html=True,
            )
        with col2:
            st.info("Depth Preview")
            st.markdown(
                '<div style="background: #1a1a1a; height: 200px; display: flex; '
                'align-items: center; justify-content: center; color: #666;">'
                "Depth map will appear here</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # Real-time quality metrics
    st.subheader("Quality Metrics (Real-time)")

    # Get metrics from session or use defaults
    if session and isinstance(session, CaptureSession):
        metrics = session.metrics
        depth_ratio = metrics.depth_valid_ratio_mean
        blur_score = metrics.blur_score_mean
        coverage = metrics.coverage_score
        num_frames = metrics.num_frames
        is_running = session.is_running
    else:
        depth_ratio = 0.0
        blur_score = 0.0
        coverage = 0.0
        num_frames = 0
        is_running = False

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Depth Valid", f"{depth_ratio:.0%}")
        st.progress(depth_ratio)

    with col2:
        st.metric("Sharpness", f"{blur_score:.0%}")
        st.progress(blur_score)

    with col3:
        st.metric("Coverage", f"{coverage:.0%}")
        st.progress(coverage)

    with col4:
        st.metric("Frames", f"{num_frames} / {target_keyframes}")
        progress = min(num_frames / target_keyframes, 1.0) if target_keyframes > 0 else 0.0
        st.progress(progress)

    st.divider()

    # Coverage map
    st.subheader("Coverage Map")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Spherical coverage visualization (placeholder)
        # Calculate region coverages based on overall coverage
        region_coverage = int(coverage * 100)
        top_coverage = max(0, min(100, region_coverage - 30))
        side_coverage = max(0, min(100, region_coverage + 10))
        bottom_coverage = max(0, min(100, region_coverage - 40))

        st.markdown(
            """
        ```
                    TOP
                  ░░░░░░░
                ░░░░░░░░░░░
              ░░░░░░░░░░░░░░░
        SIDE ░░░░░░███░░░░░░░ SIDE
              ░░░░░░░░░░░░░░░
                ░░░░░░░░░░░
                  ░░░░░░░
                  BOTTOM
        ```
        """
        )
        st.caption("░ = Not captured, █ = Captured, Coverage shows camera positions")

    with col2:
        st.markdown("**Coverage by Region**")
        st.text(f"Top:     {top_coverage}%")
        st.text(f"Side:    {side_coverage}%")
        st.text(f"Bottom:  {bottom_coverage}%")
        st.text(f"Overall: {region_coverage}%")

    st.divider()

    # Frame history
    if session and isinstance(session, CaptureSession) and session.frames:
        st.subheader("Captured Frames")

        frames_to_show = session.frames[-5:]
        cols = st.columns(min(5, len(frames_to_show)))

        for i, frame in enumerate(frames_to_show):
            with cols[i]:
                st.text(f"Frame {frame.frame_id}")
                if frame.quality.is_keyframe:
                    st.success("PASS")
                else:
                    st.warning("WARN")

    st.divider()

    # Control buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Back to Plan", use_container_width=True):
            st.session_state.navigate_to = "capture_plan"
            st.rerun()

    with col2:
        if is_running:
            if st.button("Stop Capture", type="secondary", use_container_width=True):
                if session and isinstance(session, CaptureSession):
                    stopped_session = capture_service.stop_session(session)
                    st.session_state.capture_session = stopped_session
                st.success("Capture stopped")
                st.rerun()
        else:
            if st.button("Start Capture", type="primary", use_container_width=True):
                # Start a new capture session
                new_session = capture_service.start_session(
                    object_id=selected_object.id,
                    target_keyframes=target_keyframes,
                )
                st.session_state.capture_session = new_session

                # Get initial preview frame
                result = capture_service.capture_frame(new_session)
                if result:
                    frame, rgb, depth = result
                    st.session_state.current_frame = (rgb, depth)

                st.info("Capture session started")
                st.rerun()

    with col3:
        capture_button_clicked = st.button(
            "Capture Frame", use_container_width=True, disabled=not is_running
        )
        if capture_button_clicked and session and isinstance(session, CaptureSession):
            # Capture a new frame
            result = capture_service.capture_frame(session)
            if result:
                frame, rgb, depth = result

                # Save the frame
                saved_frame = capture_service.save_frame(session, frame, rgb, depth)

                # Add frame to session
                updated_session = capture_service.add_frame_to_session(
                    session, saved_frame
                )
                st.session_state.capture_session = updated_session
                st.session_state.current_frame = (rgb, depth)

            st.rerun()

    with col4:
        can_proceed = num_frames >= 10  # Minimum frames

        if st.button(
            "Proceed to Preprocess",
            type="primary" if can_proceed else "secondary",
            use_container_width=True,
            disabled=not can_proceed,
        ):
            # Stop session if running
            if session and isinstance(session, CaptureSession) and session.is_running:
                stopped_session = capture_service.stop_session(session)
                st.session_state.capture_session = stopped_session

            # Update object stage
            selected_object.current_stage = PipelineStage.CAPTURE
            st.session_state.selected_object = selected_object

            st.success("Capture complete!")
            st.session_state.navigate_to = "preprocess"
            st.rerun()

    if not can_proceed:
        st.caption(f"Capture at least 10 frames to proceed (current: {num_frames})")


# Run the page when loaded directly by Streamlit
render_capture()
