"""Dashboard page - overview of scan2mesh GUI status."""

import streamlit as st

from scan2mesh_gui.components.metrics_display import (
    render_metric_card,
    render_quality_badge,
)
from scan2mesh_gui.models.scan_object import PipelineStage, QualityStatus


def render_dashboard() -> None:
    """Render the dashboard page."""
    st.title("Dashboard")
    st.markdown(
        '<p style="color: var(--color-text-muted); font-size: 1rem; margin-bottom: 2rem;">'
        "Welcome to scan2mesh GUI - 3D Scanning Pipeline Manager</p>",
        unsafe_allow_html=True,
    )

    # Summary metrics
    st.subheader("Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    # Get counts from session state
    profiles = st.session_state.get("profiles", [])
    current_profile = st.session_state.get("current_profile")
    status_counts = st.session_state.get("status_counts", {})

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

    with col3:
        render_metric_card(
            "PASS",
            status_counts.get(QualityStatus.PASS, 0),
            status=QualityStatus.PASS,
        )

    with col4:
        render_metric_card(
            "WARN",
            status_counts.get(QualityStatus.WARN, 0),
            status=QualityStatus.WARN,
        )

    with col5:
        render_metric_card(
            "FAIL",
            status_counts.get(QualityStatus.FAIL, 0),
            status=QualityStatus.FAIL,
        )

    # Pipeline stage breakdown
    st.subheader("Pipeline Progress")
    stage_counts = st.session_state.get("stage_counts", {})

    # Create columns for each pipeline stage
    stage_cols = st.columns(8)
    stage_labels = [
        ("Init", PipelineStage.INIT),
        ("Plan", PipelineStage.PLAN),
        ("Capture", PipelineStage.CAPTURE),
        ("Preprocess", PipelineStage.PREPROCESS),
        ("Reconstruct", PipelineStage.RECONSTRUCT),
        ("Optimize", PipelineStage.OPTIMIZE),
        ("Package", PipelineStage.PACKAGE),
        ("Report", PipelineStage.REPORT),
    ]

    for col, (label, stage) in zip(stage_cols, stage_labels, strict=False):
        with col:
            count = stage_counts.get(stage, 0)
            st.metric(label=label, value=count)

    # Recent scans
    st.subheader("Recent Scans")

    recent_objects = st.session_state.get("recent_objects", [])

    if not recent_objects:
        st.info("No recent scans. Create a profile and start scanning!")

        if st.button("Create Profile"):
            st.session_state.navigate_to = "profiles"
            st.rerun()
    else:
        # Display recent objects as a table with click to navigate
        for i, obj in enumerate(recent_objects[:10]):
            col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 2, 1])
            with col1:
                st.write(obj.display_name)
            with col2:
                st.write(obj.current_stage.value.capitalize())
            with col3:
                render_quality_badge(obj.quality_status, size="small")
            with col4:
                if obj.updated_at:
                    st.write(obj.updated_at.strftime("%Y-%m-%d %H:%M"))
            with col5:
                if st.button("View", key=f"view_obj_{i}"):
                    # Navigate to registry with selected object
                    st.session_state.selected_object = obj
                    st.session_state.current_profile_id = obj.profile_id
                    st.session_state.navigate_to = "registry"
                    st.rerun()

    # System status card
    st.subheader("System Status")

    col1, col2 = st.columns(2)

    with col1:
        realsense_connected = st.session_state.get("realsense_connected", False)
        device = st.session_state.get("realsense_device")
        if realsense_connected and device:
            st.markdown(
                f"""
                <div class="precision-card precision-card-accent" style="border-left-color: var(--color-accent-success);">
                    <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                        <span class="status-dot status-dot-success"></span>
                        <span style="color: var(--color-text-primary); font-weight: 600;">RealSense Camera</span>
                    </div>
                    <p style="color: var(--color-accent-success); font-family: 'JetBrains Mono', monospace;
                              font-size: 0.875rem; margin: 0;">{device.name}</p>
                    <p style="color: var(--color-text-secondary); font-size: 0.75rem; margin: 0.25rem 0 0 0;">
                        Serial: {device.serial_number}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="precision-card" style="border-left: 3px solid var(--color-accent-warning);">
                    <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                        <span class="status-dot status-dot-warning"></span>
                        <span style="color: var(--color-text-primary); font-weight: 600;">RealSense Camera</span>
                    </div>
                    <p style="color: var(--color-accent-warning); font-size: 0.875rem; margin: 0;">Not connected</p>
                    <p style="color: var(--color-text-secondary); font-size: 0.75rem; margin: 0.25rem 0 0 0;">
                        Connect a RealSense camera to start scanning</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col2:
        gpu_available = st.session_state.get("gpu_available", False)
        gpu_name = st.session_state.get("gpu_name", "Unknown")
        if gpu_available:
            st.markdown(
                f"""
                <div class="precision-card precision-card-accent" style="border-left-color: var(--color-accent-success);">
                    <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                        <span class="status-dot status-dot-success"></span>
                        <span style="color: var(--color-text-primary); font-weight: 600;">GPU Acceleration</span>
                    </div>
                    <p style="color: var(--color-accent-success); font-family: 'JetBrains Mono', monospace;
                              font-size: 0.875rem; margin: 0;">{gpu_name}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="precision-card" style="border-left: 3px solid var(--color-accent-info);">
                    <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                        <span class="status-dot status-dot-neutral"></span>
                        <span style="color: var(--color-text-primary); font-weight: 600;">GPU Acceleration</span>
                    </div>
                    <p style="color: var(--color-accent-info); font-size: 0.875rem; margin: 0;">CPU Mode</p>
                    <p style="color: var(--color-text-secondary); font-size: 0.75rem; margin: 0.25rem 0 0 0;">
                        Processing will be slower without GPU</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

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
