"""Dashboard page - overview of scan2mesh GUI status."""

import streamlit as st

from scan2mesh_gui.components.metrics_display import (
    render_metric_card,
    render_quality_badge,
)
from scan2mesh_gui.models.scan_object import QualityStatus


def render_dashboard() -> None:
    """Render the dashboard page."""
    st.title("Dashboard")
    st.markdown("Welcome to scan2mesh GUI - 3D Scanning Pipeline Manager")

    # Summary metrics
    st.subheader("Overview")

    col1, col2, col3, col4 = st.columns(4)

    # Get counts from session state
    profiles = st.session_state.get("profiles", [])
    current_profile = st.session_state.get("current_profile")

    with col1:
        render_metric_card(
            "Profiles",
            len(profiles),
        )

    with col2:
        object_count = st.session_state.get("object_count", 0)
        render_metric_card(
            "Objects",
            object_count,
        )

    status_counts = st.session_state.get("status_counts", {})
    with col3:
        render_metric_card(
            "PASS",
            status_counts.get(QualityStatus.PASS, 0),
            status=QualityStatus.PASS,
        )

    with col4:
        in_progress = status_counts.get(QualityStatus.PENDING, 0)
        render_metric_card(
            "In Progress",
            in_progress,
        )

    # Recent scans
    st.subheader("Recent Scans")

    recent_objects = st.session_state.get("recent_objects", [])

    if not recent_objects:
        st.info("No recent scans. Create a profile and start scanning!")

        if st.button("Create Profile"):
            st.session_state.navigate_to = "profiles"
            st.rerun()
    else:
        # Display recent objects as a table
        for obj in recent_objects[:10]:
            col1, col2, col3, col4 = st.columns([3, 2, 1, 2])
            with col1:
                st.write(obj.display_name)
            with col2:
                st.write(obj.current_stage.value.capitalize())
            with col3:
                render_quality_badge(obj.quality_status, size="small")
            with col4:
                if obj.updated_at:
                    st.write(obj.updated_at.strftime("%Y-%m-%d %H:%M"))

    # System status card
    st.subheader("System Status")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**RealSense Camera**")
        realsense_connected = st.session_state.get("realsense_connected", False)
        if realsense_connected:
            device = st.session_state.get("realsense_device")
            if device:
                st.success(f"Connected: {device.name}")
                st.caption(f"Serial: {device.serial_number}")
            else:
                st.success("Connected")
        else:
            st.warning("Not connected")
            st.caption("Connect a RealSense camera to start scanning")

    with col2:
        st.markdown("**GPU Acceleration**")
        gpu_available = st.session_state.get("gpu_available", False)
        if gpu_available:
            gpu_name = st.session_state.get("gpu_name", "Unknown")
            st.success(f"Available: {gpu_name}")
        else:
            st.info("CPU Mode")
            st.caption("Processing will be slower without GPU")

    # Quick actions
    st.subheader("Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("New Profile", use_container_width=True):
            st.session_state.navigate_to = "profiles"
            st.rerun()

    with col2:
        if current_profile:
            if st.button("Add Object", use_container_width=True):
                st.session_state.navigate_to = "registry"
                st.rerun()
        else:
            st.button("Add Object", use_container_width=True, disabled=True)
            st.caption("Select a profile first")

    with col3:
        if st.button("Check Devices", use_container_width=True):
            st.session_state.navigate_to = "devices"
            st.rerun()


# Run the page when loaded directly by Streamlit
render_dashboard()
