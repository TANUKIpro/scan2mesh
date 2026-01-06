"""Main entry point for scan2mesh GUI application."""

import streamlit as st

from scan2mesh_gui.components.sidebar import render_sidebar
from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.services.device_service import DeviceService
from scan2mesh_gui.services.profile_service import ProfileService


def init_session_state() -> None:
    """Initialize session state variables."""
    defaults: dict[str, object] = {
        "current_page": "dashboard",
        "current_profile": None,
        "profiles": [],
        "selected_object": None,
        "object_count": 0,
        "status_counts": {},
        "recent_objects": [],
        "realsense_connected": False,
        "realsense_device": None,
        "gpu_available": False,
        "gpu_name": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_initial_data() -> None:
    """Load initial data into session state."""
    config = get_config_manager()

    # Load profiles
    profile_service = ProfileService(config.profiles_dir)
    st.session_state.profiles = profile_service.list_profiles()

    # Check device status
    device_service = DeviceService()
    devices = device_service.list_devices()
    st.session_state.realsense_connected = len(devices) > 0
    if devices:
        st.session_state.realsense_device = devices[0]

    # Check GPU availability (simplified check)
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            st.session_state.gpu_available = True
            st.session_state.gpu_name = result.stdout.strip().split("\n")[0]
    except Exception:
        st.session_state.gpu_available = False
        st.session_state.gpu_name = None


def main() -> None:
    """Main application entry point."""
    # Page config
    st.set_page_config(
        page_title="scan2mesh GUI",
        page_icon=":camera:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for consistent styling
    st.markdown(
        """
        <style>
        /* Remove extra padding */
        .block-container {
            padding-top: 2rem;
        }

        /* Style sidebar */
        [data-testid="stSidebar"] {
            background-color: #f8f9fa;
        }

        /* Style buttons */
        .stButton button {
            border-radius: 4px;
        }

        /* Style dividers */
        hr {
            margin: 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Initialize
    init_session_state()

    # Load data on first run
    if "data_loaded" not in st.session_state:
        load_initial_data()
        st.session_state.data_loaded = True

    # Render sidebar and get current page
    current_page = render_sidebar()
    st.session_state.current_page = current_page

    # Route to appropriate page
    render_page(current_page)


def render_page(page: str) -> None:
    """Render the appropriate page based on navigation."""
    from scan2mesh_gui.pages.dashboard import render_dashboard
    from scan2mesh_gui.pages.devices import render_devices
    from scan2mesh_gui.pages.profiles import render_profiles
    from scan2mesh_gui.pages.registry import render_registry
    from scan2mesh_gui.pages.settings import render_settings

    pages = {
        "dashboard": render_dashboard,
        "profiles": render_profiles,
        "registry": render_registry,
        "devices": render_devices,
        "settings": render_settings,
    }

    # Pipeline pages (placeholders)
    pipeline_pages = [
        "capture_plan",
        "capture",
        "preprocess",
        "reconstruct",
        "optimize",
        "package",
        "report",
    ]

    if page in pages:
        pages[page]()
    elif page in pipeline_pages:
        render_pipeline_placeholder(page)
    else:
        st.error(f"Unknown page: {page}")


def render_pipeline_placeholder(page: str) -> None:
    """Render a placeholder for pipeline pages not yet implemented."""
    page_titles = {
        "capture_plan": "Capture Plan",
        "capture": "Capture",
        "preprocess": "Preprocess",
        "reconstruct": "Reconstruct",
        "optimize": "Optimize",
        "package": "Package",
        "report": "Report",
    }

    st.title(page_titles.get(page, page.capitalize()))
    st.info("This page is under development.")

    # Show selected object if any
    selected_object = st.session_state.get("selected_object")
    if selected_object:
        st.markdown(f"**Selected Object:** {selected_object.display_name}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Go Back"):
                st.session_state.navigate_to = "registry"
                st.rerun()
        with col2:
            next_pages = {
                "capture_plan": "capture",
                "capture": "preprocess",
                "preprocess": "reconstruct",
                "reconstruct": "optimize",
                "optimize": "package",
                "package": "report",
                "report": "dashboard",
            }
            next_page = next_pages.get(page)
            if next_page:
                if st.button(f"Next: {page_titles.get(next_page, next_page).capitalize()}"):
                    st.session_state.navigate_to = next_page
                    st.rerun()
    else:
        st.warning("No object selected. Please select an object from the Registry.")
        if st.button("Go to Registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()


if __name__ == "__main__":
    main()
