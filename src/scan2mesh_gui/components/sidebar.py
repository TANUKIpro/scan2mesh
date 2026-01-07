"""Sidebar component with navigation and system status."""

from typing import TYPE_CHECKING

import streamlit as st

from scan2mesh_gui.models.scan_object import PipelineStage


if TYPE_CHECKING:
    from scan2mesh_gui.models.profile import Profile


# Navigation items with icons (using emoji for better dark theme compatibility)
NAVIGATION_ITEMS = [
    ("Dashboard", "dashboard", "📊"),
    ("Profiles", "profiles", "📁"),
    ("Registry", "registry", "🗄️"),
    ("Devices", "devices", "📷"),
    ("---", None, None),  # Separator
    ("Capture Plan", "capture_plan", "🗺️"),
    ("Capture", "capture", "🎬"),
    ("Preprocess", "preprocess", "⚙️"),
    ("Reconstruct", "reconstruct", "📦"),
    ("Optimize", "optimize", "🎚️"),
    ("Package", "package", "📤"),
    ("Report", "report", "📄"),
    ("---", None, None),  # Separator
    ("Settings", "settings", "⚙️"),
]


def render_sidebar() -> str:
    """Render the sidebar and return the selected page."""
    with st.sidebar:
        # Logo and title with Precision Lab styling
        st.markdown(
            """
            <div class="app-logo">
                <div class="app-logo-title">scan2mesh</div>
                <div class="app-logo-subtitle">3D Scanner</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Theme toggle
        render_theme_toggle()

        st.markdown(
            '<hr style="margin: 0.5rem 0; border-color: var(--color-border);">',
            unsafe_allow_html=True,
        )

        # Profile selector
        render_profile_selector()

        st.markdown(
            '<hr style="margin: 0.5rem 0; border-color: var(--color-border);">',
            unsafe_allow_html=True,
        )

        # Navigation
        selected_page = render_navigation()

        st.markdown(
            '<hr style="margin: 0.5rem 0; border-color: var(--color-border);">',
            unsafe_allow_html=True,
        )

        # System status
        render_system_status()

        return selected_page


def render_theme_toggle() -> None:
    """Render the theme toggle switch."""
    current_theme = st.session_state.get("theme", "light")
    is_dark = current_theme == "dark"

    # Theme toggle with icons
    col1, col2 = st.columns([1, 1])

    with col1:
        light_btn_type = "secondary" if is_dark else "primary"
        light_clicked = st.button(
            "☀️ Light",
            key="theme_light",
            use_container_width=True,
            type=light_btn_type,
        )
        if light_clicked and is_dark:
            st.session_state.theme = "light"
            st.rerun()

    with col2:
        dark_btn_type = "primary" if is_dark else "secondary"
        dark_clicked = st.button(
            "🌙 Dark",
            key="theme_dark",
            use_container_width=True,
            type=dark_btn_type,
        )
        if dark_clicked and not is_dark:
            st.session_state.theme = "dark"
            st.rerun()


def render_profile_selector() -> None:
    """Render the profile selector dropdown."""
    st.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: var(--color-text-muted); '
        'text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">'
        "Current Profile</p>",
        unsafe_allow_html=True,
    )

    # Get profiles from session state
    profiles: list[Profile] = st.session_state.get("profiles", [])
    current_profile: Profile | None = st.session_state.get("current_profile")

    if not profiles:
        st.markdown(
            """
            <div style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3);
                        border-radius: 6px; padding: 0.75rem; text-align: center;">
                <p style="color: var(--color-text-secondary); font-size: 0.8rem; margin: 0;">No profiles yet</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("+ Create Profile", key="sidebar_create_profile", use_container_width=True):
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

    # Section label for main navigation
    st.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: var(--color-text-muted); '
        'text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">'
        "Navigation</p>",
        unsafe_allow_html=True,
    )

    for label, page_key, icon in NAVIGATION_ITEMS:
        if page_key is None:
            # Separator
            st.markdown(
                '<hr style="margin: 0.75rem 0 0.5rem 0; border-color: var(--color-border);">',
                unsafe_allow_html=True,
            )
            continue

        # Determine if this is the active page
        is_active = current_page == page_key

        # Use button with appropriate type based on active state
        button_type = "primary" if is_active else "secondary"
        clicked = st.button(
            f"{icon}  {label}",
            key=f"nav_{page_key}",
            use_container_width=True,
            type=button_type,
        )
        if clicked and not is_active:
            st.session_state.current_page = page_key
            st.rerun()

    return str(current_page)


def render_system_status() -> None:
    """Render the system status indicators."""
    from scan2mesh_gui.services.device_service import DeviceService

    st.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: var(--color-text-muted); '
        'text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem;">'
        "System Status</p>",
        unsafe_allow_html=True,
    )

    # RealSense status
    realsense_connected = st.session_state.get("realsense_connected", False)
    if realsense_connected:
        st.markdown(
            '<div style="display: flex; align-items: center; margin-bottom: 0.5rem;">'
            '<span class="status-dot status-dot-success"></span>'
            '<span style="color: var(--color-text-primary); font-size: 0.85rem;">RealSense</span>'
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="display: flex; align-items: center; margin-bottom: 0.5rem;">'
            '<span class="status-dot status-dot-danger"></span>'
            '<span style="color: var(--color-text-secondary); font-size: 0.85rem;">RealSense</span>'
            "</div>",
            unsafe_allow_html=True,
        )

    # Selected device
    service = DeviceService()
    selected_device = service.get_selected_device()
    if selected_device:
        st.markdown(
            f'<p style="color: var(--color-accent-primary); font-size: 0.75rem; margin: 0 0 0.75rem 1rem; '
            f'font-family: \'JetBrains Mono\', monospace;">'
            f"{selected_device.name[:20]}</p>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="color: var(--color-text-muted); font-size: 0.75rem; margin: 0 0 0.75rem 1rem;">'
            "No device selected</p>",
            unsafe_allow_html=True,
        )

    # GPU status
    gpu_available = st.session_state.get("gpu_available", False)
    if gpu_available:
        st.markdown(
            '<div style="display: flex; align-items: center;">'
            '<span class="status-dot status-dot-success"></span>'
            '<span style="color: var(--color-text-primary); font-size: 0.85rem;">GPU Ready</span>'
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="display: flex; align-items: center;">'
            '<span class="status-dot status-dot-warning"></span>'
            '<span style="color: var(--color-text-secondary); font-size: 0.85rem;">CPU Mode</span>'
            "</div>",
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
