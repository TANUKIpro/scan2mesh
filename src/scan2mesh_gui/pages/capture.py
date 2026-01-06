"""Capture page - real-time RGB-D capture with quality monitoring."""

import streamlit as st

from scan2mesh_gui.components.camera_preview import render_camera_preview
from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.device_service import DeviceService
from scan2mesh_gui.services.pipeline_service import PipelineService


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

    # Check for camera connection
    device_service = DeviceService()
    devices = device_service.list_devices()

    if not devices:
        st.error("No RealSense camera detected")
        if st.button("Go to Devices"):
            st.session_state.navigate_to = "devices"
            st.rerun()
        return

    device = devices[0]
    config = get_config_manager()
    pipeline = PipelineService(config.projects_dir)

    # Initialize capture state
    if "capture_running" not in st.session_state:
        st.session_state.capture_running = False
    if "captured_frames" not in st.session_state:
        st.session_state.captured_frames = 0
    if "capture_metrics" not in st.session_state:
        st.session_state.capture_metrics = {
            "depth_valid_ratio": 0.0,
            "blur_score": 0.0,
            "coverage": 0.0,
        }

    # Capture plan info
    capture_plan = st.session_state.get("capture_plan", {})
    target_keyframes = capture_plan.get("target_keyframes", 36)

    # Camera preview section
    st.subheader("Camera Preview")

    col1, col2 = st.columns(2)

    # Get test frame for preview
    test_frame = st.session_state.get("current_frame")
    if test_frame:
        rgb, depth = test_frame
        render_camera_preview(rgb, depth)
    else:
        with col1:
            st.info("RGB Preview")
            st.markdown(
                '<div style="background: #1a1a1a; height: 200px; display: flex; align-items: center; justify-content: center; color: #666;">Camera feed will appear here</div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.info("Depth Preview")
            st.markdown(
                '<div style="background: #1a1a1a; height: 200px; display: flex; align-items: center; justify-content: center; color: #666;">Depth map will appear here</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # Real-time quality metrics
    st.subheader("Quality Metrics (Real-time)")

    metrics = st.session_state.capture_metrics

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        depth_ratio = metrics.get("depth_valid_ratio", 0.0)
        st.metric("Depth Valid", f"{depth_ratio:.0%}")
        st.progress(depth_ratio)

    with col2:
        blur_score = metrics.get("blur_score", 0.0)
        st.metric("Sharpness", f"{blur_score:.0%}")
        st.progress(blur_score)

    with col3:
        coverage = metrics.get("coverage", 0.0)
        st.metric("Coverage", f"{coverage:.0%}")
        st.progress(coverage)

    with col4:
        frames = st.session_state.captured_frames
        st.metric("Frames", f"{frames} / {target_keyframes}")
        st.progress(min(frames / target_keyframes, 1.0))

    st.divider()

    # Coverage map
    st.subheader("Coverage Map")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Spherical coverage visualization (placeholder)
        st.markdown("""
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
        """)
        st.caption("░ = Not captured, █ = Captured, Coverage shows camera positions")

    with col2:
        st.markdown("**Coverage by Region**")
        st.text(f"Top:     {20}%")
        st.text(f"Side:    {60}%")
        st.text(f"Bottom:  {10}%")
        st.text(f"Overall: {30}%")

    st.divider()

    # Frame history
    if st.session_state.captured_frames > 0:
        st.subheader("Captured Frames")

        frame_history = st.session_state.get("frame_history", [])
        if frame_history:
            cols = st.columns(min(5, len(frame_history)))
            for i, frame_info in enumerate(frame_history[-5:]):
                with cols[i]:
                    st.text(f"Frame {frame_info['id']}")
                    quality = frame_info.get("quality", "pending")
                    if quality == "pass":
                        st.success("PASS")
                    elif quality == "warn":
                        st.warning("WARN")
                    else:
                        st.info("...")

    st.divider()

    # Control buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Back to Plan", use_container_width=True):
            st.session_state.navigate_to = "capture_plan"
            st.rerun()

    with col2:
        if st.session_state.capture_running:
            if st.button("Stop Capture", type="secondary", use_container_width=True):
                st.session_state.capture_running = False
                st.success("Capture stopped")
                st.rerun()
        else:
            if st.button("Start Capture", type="primary", use_container_width=True):
                st.session_state.capture_running = True
                st.info("Starting capture...")

                # Simulate starting capture
                result = device_service.test_capture(device.serial_number)
                if result:
                    rgb, depth = result
                    st.session_state.current_frame = (rgb, depth)

                    # Update metrics (simulated)
                    st.session_state.capture_metrics = {
                        "depth_valid_ratio": 0.85,
                        "blur_score": 0.78,
                        "coverage": 0.25,
                    }
                    st.session_state.captured_frames = 5

                st.rerun()

    with col3:
        if st.button("Capture Frame", use_container_width=True, disabled=not st.session_state.capture_running):
            # Simulate capturing a frame
            st.session_state.captured_frames += 1

            # Add to frame history
            frame_history = st.session_state.get("frame_history", [])
            frame_history.append({
                "id": st.session_state.captured_frames,
                "quality": "pass" if st.session_state.captured_frames % 3 != 0 else "warn",
            })
            st.session_state.frame_history = frame_history

            # Update metrics
            coverage = min(st.session_state.captured_frames / target_keyframes, 1.0)
            st.session_state.capture_metrics["coverage"] = coverage * 0.9

            st.rerun()

    with col4:
        can_proceed = st.session_state.captured_frames >= 10  # Minimum frames

        if st.button(
            "Proceed to Preprocess",
            type="primary" if can_proceed else "secondary",
            use_container_width=True,
            disabled=not can_proceed,
        ):
            # Update object stage
            selected_object.current_stage = PipelineStage.CAPTURE
            st.session_state.selected_object = selected_object
            st.session_state.capture_running = False

            st.success("Capture complete!")
            st.session_state.navigate_to = "preprocess"
            st.rerun()

    if not can_proceed:
        st.caption(f"Capture at least 10 frames to proceed (current: {st.session_state.captured_frames})")


# Run the page when loaded directly by Streamlit
render_capture()
