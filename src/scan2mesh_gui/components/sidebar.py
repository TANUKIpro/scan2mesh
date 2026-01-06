"""Sidebar component with navigation and system status."""

from typing import TYPE_CHECKING

import streamlit as st

from scan2mesh_gui.models.scan_object import PipelineStage


if TYPE_CHECKING:
    from scan2mesh_gui.models.profile import Profile


# Navigation items with icons
NAVIGATION_ITEMS = [
    ("Dashboard", "dashboard", "house"),
    ("Profiles", "profiles", "folder"),
    ("Registry", "registry", "database"),
    ("Devices", "devices", "camera"),
    ("---", None, None),  # Separator
    ("Capture Plan", "capture_plan", "map"),
    ("Capture", "capture", "camera-video"),
    ("Preprocess", "preprocess", "gear"),
    ("Reconstruct", "reconstruct", "boxes"),
    ("Optimize", "optimize", "sliders"),
    ("Package", "package", "box-seam"),
    ("Report", "report", "file-earmark-text"),
    ("---", None, None),  # Separator
    ("Settings", "settings", "gear-fill"),
]


def render_sidebar() -> str:
    """Render the sidebar and return the selected page."""
    with st.sidebar:
        # Logo and title
        st.markdown(
            """
            <div style="text-align: center; padding: 1rem 0;">
                <h2 style="margin: 0;">scan2mesh</h2>
                <p style="color: #6c757d; margin: 0;">GUI</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Profile selector
        render_profile_selector()

        st.divider()

        # Navigation
        selected_page = render_navigation()

        st.divider()

        # System status
        render_system_status()

        return selected_page


def render_profile_selector() -> None:
    """Render the profile selector dropdown."""
    st.markdown("**Profile**")

    # Get profiles from session state
    profiles: list[Profile] = st.session_state.get("profiles", [])
    current_profile: Profile | None = st.session_state.get("current_profile")

    if not profiles:
        st.info("No profiles yet")
        if st.button("Create Profile", key="sidebar_create_profile"):
            st.session_state.navigate_to = "profiles"
            st.rerun()
        return

    # Profile dropdown
    profile_names = [p.name for p in profiles]
    current_index = 0
    if current_profile:
        for i, p in enumerate(profiles):
            if p.id == current_profile.id:
                current_index = i
                break

    selected_name = st.selectbox(
        "Select profile",
        profile_names,
        index=current_index,
        label_visibility="collapsed",
    )

    # Update current profile
    for p in profiles:
        if p.name == selected_name:
            if current_profile is None or p.id != current_profile.id:
                st.session_state.current_profile = p
                st.rerun()
            break


def render_navigation() -> str:
    """Render the navigation menu and return selected page."""
    current_page = st.session_state.get("current_page", "dashboard")

    # Check for navigation request
    if "navigate_to" in st.session_state:
        current_page = st.session_state.navigate_to
        del st.session_state.navigate_to

    for label, page_key, icon in NAVIGATION_ITEMS:
        if page_key is None:
            # Separator
            st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
            continue

        # Determine if this is the active page
        is_active = current_page == page_key

        if st.button(
            f":{icon}: {label}" if icon else label,
            key=f"nav_{page_key}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.current_page = page_key
            st.rerun()

    return str(current_page)


def render_system_status() -> None:
    """Render the system status indicators."""
    from scan2mesh_gui.services.device_service import DeviceService

    st.markdown("**System Status**")

    # RealSense status
    realsense_connected = st.session_state.get("realsense_connected", False)
    if realsense_connected:
        st.markdown(
            '<span style="color: #28a745;">● RealSense Connected</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span style="color: #dc3545;">○ RealSense Disconnected</span>',
            unsafe_allow_html=True,
        )

    # Selected device
    service = DeviceService()
    selected_device = service.get_selected_device()
    if selected_device:
        st.markdown(
            f'<span style="color: #007bff; font-size: 12px;">'
            f'Using: {selected_device.name[:20]}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span style="color: #6c757d; font-size: 12px;">No device selected</span>',
            unsafe_allow_html=True,
        )

    # GPU status
    gpu_available = st.session_state.get("gpu_available", False)
    if gpu_available:
        st.markdown(
            '<span style="color: #28a745;">● GPU Available</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span style="color: #ffc107;">○ CPU Mode</span>',
            unsafe_allow_html=True,
        )


def get_stage_icon(stage: PipelineStage) -> str:
    """Get the icon for a pipeline stage."""
    icons = {
        PipelineStage.INIT: "flag",
        PipelineStage.PLAN: "map",
        PipelineStage.CAPTURE: "camera-video",
        PipelineStage.PREPROCESS: "gear",
        PipelineStage.RECONSTRUCT: "boxes",
        PipelineStage.OPTIMIZE: "sliders",
        PipelineStage.PACKAGE: "box-seam",
        PipelineStage.REPORT: "file-earmark-text",
    }
    return icons.get(stage, "circle")
