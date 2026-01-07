"""Main entry point for scan2mesh GUI application."""

import streamlit as st

from scan2mesh_gui.components.sidebar import render_sidebar
from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.services.device_service import DeviceService
from scan2mesh_gui.services.object_service import ObjectService
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
        "stage_counts": {},
        "recent_objects": [],
        "all_objects": [],
        "realsense_connected": False,
        "realsense_device": None,
        "gpu_available": False,
        "gpu_name": None,
        "theme": "light",  # Default to light mode
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

    # Load dashboard data - all objects across all profiles
    profile_ids = [p.id for p in st.session_state.profiles]
    object_service = ObjectService(config.profiles_dir, config.projects_dir)

    # Get all objects (for recent scans list)
    all_objects = object_service.list_all_objects(profile_ids)
    st.session_state.all_objects = all_objects
    st.session_state.recent_objects = all_objects[:10]  # Most recent 10
    st.session_state.object_count = len(all_objects)

    # Get status counts (PASS/WARN/FAIL/PENDING)
    st.session_state.status_counts = object_service.get_all_status_counts(profile_ids)

    # Get stage counts (Init/Plan/Capture/...)
    st.session_state.stage_counts = object_service.get_stage_counts(profile_ids)

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


def get_theme_css(theme: str) -> str:
    """Generate CSS for the specified theme.

    Args:
        theme: Either "light" or "dark"

    Returns:
        CSS string for the theme
    """
    if theme == "light":
        return """
        /* CSS Variables - Light Mode */
        :root {
            --color-bg-primary: #f8fafc;
            --color-bg-secondary: #ffffff;
            --color-bg-tertiary: #f1f5f9;
            --color-bg-elevated: #ffffff;
            --color-accent-primary: #00a884;
            --color-accent-secondary: #3b82f6;
            --color-accent-success: #16a34a;
            --color-accent-warning: #d97706;
            --color-accent-danger: #dc2626;
            --color-text-primary: #1e293b;
            --color-text-secondary: #475569;
            --color-text-muted: #94a3b8;
            --color-border: rgba(0,0,0,0.08);
            --color-border-hover: rgba(0,0,0,0.15);
            --color-glow: rgba(0,168,132,0.15);
            --font-display: 'JetBrains Mono', monospace;
            --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
            --shadow-sm: 0 2px 4px rgba(0,0,0,0.06);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
            --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
        }
        """
    else:
        return """
        /* CSS Variables - Dark Mode */
        :root {
            --color-bg-primary: #0f1419;
            --color-bg-secondary: #1a2332;
            --color-bg-tertiary: #243044;
            --color-bg-elevated: #2d3a4f;
            --color-accent-primary: #00d4aa;
            --color-accent-secondary: #3b82f6;
            --color-accent-success: #22c55e;
            --color-accent-warning: #f59e0b;
            --color-accent-danger: #ef4444;
            --color-text-primary: #f1f5f9;
            --color-text-secondary: #94a3b8;
            --color-text-muted: #64748b;
            --color-border: rgba(255,255,255,0.08);
            --color-border-hover: rgba(255,255,255,0.15);
            --color-glow: rgba(0,212,170,0.15);
            --font-display: 'JetBrains Mono', monospace;
            --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
            --shadow-sm: 0 2px 4px rgba(0,0,0,0.3);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
            --shadow-lg: 0 8px 24px rgba(0,0,0,0.5);
        }
        """


def get_common_css() -> str:
    """Get common CSS styles shared between themes."""
    return """
        /* Google Fonts Import */
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
    """


def get_component_css(theme: str) -> str:
    """Get component CSS styles for the theme.

    Args:
        theme: Either "light" or "dark"

    Returns:
        CSS string for component styles
    """
    # Theme-specific background gradient
    if theme == "light":
        app_bg = "linear-gradient(135deg, var(--color-bg-primary) 0%, #e2e8f0 100%)"
        sidebar_bg = "linear-gradient(180deg, var(--color-bg-secondary) 0%, var(--color-bg-primary) 100%)"
    else:
        app_bg = "linear-gradient(135deg, var(--color-bg-primary) 0%, #141d2b 100%)"
        sidebar_bg = "linear-gradient(180deg, var(--color-bg-secondary) 0%, var(--color-bg-primary) 100%)"

    return f"""
        /* ========================================
           PRECISION LAB THEME - scan2mesh GUI
           A technical, refined theme for 3D scanning
           ======================================== */

        /* Hide Streamlit's default multipage navigation */
        [data-testid="stSidebarNavContainer"],
        [data-testid="stSidebarNav"],
        section[data-testid="stSidebar"] > div:first-child > div:first-child > div:first-child {{
            display: none !important;
        }}

        /* Main app background */
        .stApp {{
            background: {app_bg};
        }}

        /* Main content area */
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }}

        /* Sidebar styling */
        [data-testid="stSidebar"] {{
            background: {sidebar_bg};
            border-right: 1px solid var(--color-border);
        }}

        [data-testid="stSidebar"] > div:first-child {{
            padding-top: 1rem;
        }}

        /* Typography */
        h1, h2, h3 {{
            font-family: var(--font-display) !important;
            color: var(--color-text-primary) !important;
            letter-spacing: -0.02em;
        }}

        h1 {{
            font-size: 2.25rem !important;
            font-weight: 700 !important;
            background: linear-gradient(135deg, var(--color-text-primary) 0%, var(--color-accent-primary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        h2 {{
            font-size: 1.5rem !important;
            font-weight: 600 !important;
        }}

        h3 {{
            font-size: 1.125rem !important;
            font-weight: 600 !important;
            color: var(--color-text-secondary) !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        p, span, label, .stMarkdown {{
            font-family: var(--font-body) !important;
            color: var(--color-text-secondary);
        }}

        /* Metric styling */
        [data-testid="stMetric"] {{
            background: var(--color-bg-tertiary);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-md);
            padding: 1rem;
            transition: all 0.2s ease;
        }}

        [data-testid="stMetric"]:hover {{
            border-color: var(--color-border-hover);
            box-shadow: var(--shadow-sm);
        }}

        [data-testid="stMetricLabel"] {{
            font-family: var(--font-body) !important;
            font-size: 0.75rem !important;
            font-weight: 500 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--color-text-muted) !important;
        }}

        [data-testid="stMetricValue"] {{
            font-family: var(--font-display) !important;
            font-size: 1.75rem !important;
            font-weight: 700 !important;
            color: var(--color-text-primary) !important;
        }}

        /* Button styling */
        .stButton > button {{
            font-family: var(--font-body) !important;
            font-weight: 500;
            border-radius: var(--radius-sm);
            padding: 0.5rem 1rem;
            transition: all 0.2s ease;
            border: 1px solid var(--color-border);
            background: var(--color-bg-tertiary);
            color: var(--color-text-primary);
        }}

        .stButton > button:hover {{
            border-color: var(--color-accent-primary);
            box-shadow: 0 0 12px var(--color-glow);
            transform: translateY(-1px);
        }}

        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {{
            background: linear-gradient(135deg, var(--color-accent-primary) 0%, #00b894 100%);
            border: none;
            color: var(--color-bg-primary);
            font-weight: 600;
        }}

        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover {{
            box-shadow: 0 0 20px var(--color-glow);
        }}

        /* Input styling */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > div,
        .stTextArea > div > div > textarea {{
            font-family: var(--font-body) !important;
            background: var(--color-bg-tertiary) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: var(--radius-sm) !important;
            color: var(--color-text-primary) !important;
        }}

        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {{
            border-color: var(--color-accent-primary) !important;
            box-shadow: 0 0 0 2px var(--color-glow) !important;
        }}

        /* Selectbox dropdown */
        [data-baseweb="select"] {{
            background: var(--color-bg-tertiary) !important;
        }}

        [data-baseweb="popover"] {{
            background: var(--color-bg-elevated) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: var(--radius-md) !important;
        }}

        /* Expander styling */
        .streamlit-expanderHeader {{
            font-family: var(--font-body) !important;
            font-weight: 500;
            background: var(--color-bg-tertiary) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: var(--radius-sm) !important;
            color: var(--color-text-primary) !important;
        }}

        .streamlit-expanderContent {{
            background: var(--color-bg-secondary) !important;
            border: 1px solid var(--color-border) !important;
            border-top: none !important;
            border-radius: 0 0 var(--radius-sm) var(--radius-sm) !important;
        }}

        /* Fix expander icon display */
        [data-testid="stExpander"] summary {{
            background: var(--color-bg-tertiary) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: var(--radius-sm) !important;
            padding: 0.75rem 1rem !important;
            color: var(--color-text-primary) !important;
        }}

        [data-testid="stExpander"] summary:hover {{
            background: var(--color-bg-elevated) !important;
            border-color: var(--color-border-hover) !important;
        }}

        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
            background: var(--color-bg-secondary) !important;
            border: 1px solid var(--color-border) !important;
            border-top: none !important;
            border-radius: 0 0 var(--radius-sm) var(--radius-sm) !important;
            padding: 1rem !important;
        }}

        /* Material icons fix - hide text fallback */
        [data-testid="stExpander"] summary span[data-testid] {{
            font-family: 'Material Symbols Rounded', sans-serif !important;
        }}

        /* Divider styling */
        hr {{
            margin: 1.5rem 0;
            border: none;
            border-top: 1px solid var(--color-border);
        }}

        /* Alert/info boxes */
        .stAlert {{
            background: var(--color-bg-tertiary) !important;
            border: 1px solid var(--color-border) !important;
            border-radius: var(--radius-md) !important;
            color: var(--color-text-secondary) !important;
        }}

        [data-testid="stAlertContainer"] {{
            background: var(--color-bg-tertiary) !important;
            border-left: 4px solid var(--color-accent-secondary) !important;
        }}

        /* Success alert */
        [data-testid="stAlertContainer"][data-baseweb*="positive"],
        .element-container:has([data-testid="stAlertContainer"]) .stSuccess {{
            border-left-color: var(--color-accent-success) !important;
        }}

        /* Warning alert */
        [data-testid="stAlertContainer"][data-baseweb*="warning"] {{
            border-left-color: var(--color-accent-warning) !important;
        }}

        /* Error alert */
        [data-testid="stAlertContainer"][data-baseweb*="negative"] {{
            border-left-color: var(--color-accent-danger) !important;
        }}

        /* Slider styling */
        .stSlider > div > div > div > div {{
            background: var(--color-accent-primary) !important;
        }}

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {{
            background: var(--color-bg-tertiary);
            border-radius: var(--radius-md);
            padding: 4px;
            gap: 4px;
        }}

        .stTabs [data-baseweb="tab"] {{
            font-family: var(--font-body) !important;
            background: transparent;
            border-radius: var(--radius-sm);
            color: var(--color-text-secondary);
        }}

        .stTabs [aria-selected="true"] {{
            background: var(--color-bg-elevated);
            color: var(--color-text-primary);
        }}

        /* File uploader */
        [data-testid="stFileUploader"] {{
            background: var(--color-bg-tertiary);
            border: 2px dashed var(--color-border);
            border-radius: var(--radius-md);
            padding: 1rem;
        }}

        [data-testid="stFileUploader"]:hover {{
            border-color: var(--color-accent-primary);
        }}

        /* Scrollbar styling */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}

        ::-webkit-scrollbar-track {{
            background: var(--color-bg-primary);
        }}

        ::-webkit-scrollbar-thumb {{
            background: var(--color-bg-elevated);
            border-radius: 4px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: var(--color-text-muted);
        }}

        /* Custom classes for components */
        .precision-card {{
            background: linear-gradient(135deg, var(--color-bg-tertiary) 0%, var(--color-bg-secondary) 100%);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-md);
            padding: 1.25rem;
            transition: all 0.3s ease;
        }}

        .precision-card:hover {{
            border-color: var(--color-border-hover);
            box-shadow: var(--shadow-md);
            transform: translateY(-2px);
        }}

        .precision-card-accent {{
            border-left: 3px solid var(--color-accent-primary);
        }}

        .precision-badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            font-family: var(--font-body);
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}

        .precision-badge-success {{
            background: rgba(34, 197, 94, 0.15);
            color: var(--color-accent-success);
            border: 1px solid rgba(34, 197, 94, 0.3);
        }}

        .precision-badge-warning {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--color-accent-warning);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}

        .precision-badge-danger {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--color-accent-danger);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}

        .precision-badge-neutral {{
            background: rgba(148, 163, 184, 0.15);
            color: var(--color-text-secondary);
            border: 1px solid rgba(148, 163, 184, 0.3);
        }}

        .precision-glow {{
            box-shadow: 0 0 20px var(--color-glow);
        }}

        .precision-stat {{
            text-align: center;
            padding: 1rem;
        }}

        .precision-stat-value {{
            font-family: var(--font-display);
            font-size: 2rem;
            font-weight: 700;
            color: var(--color-text-primary);
            line-height: 1.2;
        }}

        .precision-stat-label {{
            font-family: var(--font-body);
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--color-text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.25rem;
        }}

        /* Status indicator dots */
        .status-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }}

        .status-dot-success {{
            background: var(--color-accent-success);
            box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
        }}

        .status-dot-warning {{
            background: var(--color-accent-warning);
            box-shadow: 0 0 8px rgba(245, 158, 11, 0.5);
        }}

        .status-dot-danger {{
            background: var(--color-accent-danger);
            box-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
        }}

        .status-dot-neutral {{
            background: var(--color-text-muted);
        }}

        /* Navigation item styling */
        .nav-item {{
            display: flex;
            align-items: center;
            padding: 0.625rem 0.875rem;
            margin: 0.125rem 0;
            border-radius: var(--radius-sm);
            font-family: var(--font-body);
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--color-text-secondary);
            background: transparent;
            border: 1px solid transparent;
            transition: all 0.2s ease;
            cursor: pointer;
        }}

        .nav-item:hover {{
            background: var(--color-bg-tertiary);
            color: var(--color-text-primary);
            border-color: var(--color-border);
        }}

        .nav-item-active {{
            background: linear-gradient(135deg, rgba(0,212,170,0.1) 0%, rgba(0,212,170,0.05) 100%);
            color: var(--color-accent-primary);
            border-color: rgba(0,212,170,0.3);
        }}

        .nav-item-active:hover {{
            background: linear-gradient(135deg, rgba(0,212,170,0.15) 0%, rgba(0,212,170,0.08) 100%);
            border-color: rgba(0,212,170,0.4);
        }}

        /* Logo styling */
        .app-logo {{
            text-align: center;
            padding: 1rem 0 1.5rem 0;
        }}

        .app-logo-title {{
            font-family: var(--font-display);
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--color-accent-primary) 0%, #00b894 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 0;
        }}

        .app-logo-subtitle {{
            font-family: var(--font-body);
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--color-text-muted);
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-top: 0.25rem;
        }}

        /* Hide Streamlit branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* Deploy button override for better visibility */
        [data-testid="stToolbar"] {{
            display: none !important;
        }}

        /* Hide sidebar collapse button completely */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="collapsedControl"],
        button[kind="header"] {{
            display: none !important;
        }}

        /* Style the actual collapse control if visible */
        [data-testid="collapsedControl"] {{
            background: var(--color-bg-secondary) !important;
            border: 1px solid var(--color-border) !important;
            color: var(--color-text-secondary) !important;
        }}

        /* Hide keyboard icon text fallbacks globally */
        span[class*="keyboard"],
        [data-testid="stSidebar"] span {{
            font-family: var(--font-body) !important;
        }}
    """


def main() -> None:
    """Main application entry point."""
    # Page config
    st.set_page_config(
        page_title="scan2mesh GUI",
        page_icon=":camera:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state first to get theme
    init_session_state()

    # Get current theme
    current_theme = st.session_state.get("theme", "light")
    theme_css = get_theme_css(current_theme)
    common_css = get_common_css()

    # Build CSS for theme
    component_css = get_component_css(current_theme)
    full_css = common_css + theme_css + component_css

    # Custom CSS for Precision Lab theme
    st.markdown(
        "<style>" + full_css + "</style>",
        unsafe_allow_html=True,
    )

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
    from scan2mesh_gui.pages.capture import render_capture
    from scan2mesh_gui.pages.capture_plan import render_capture_plan
    from scan2mesh_gui.pages.dashboard import render_dashboard
    from scan2mesh_gui.pages.devices import render_devices
    from scan2mesh_gui.pages.optimize import render_optimize
    from scan2mesh_gui.pages.package import render_package
    from scan2mesh_gui.pages.preprocess import render_preprocess
    from scan2mesh_gui.pages.profiles import render_profiles
    from scan2mesh_gui.pages.reconstruct import render_reconstruct
    from scan2mesh_gui.pages.registry import render_registry
    from scan2mesh_gui.pages.report import render_report
    from scan2mesh_gui.pages.settings import render_settings

    pages = {
        "dashboard": render_dashboard,
        "profiles": render_profiles,
        "registry": render_registry,
        "devices": render_devices,
        "settings": render_settings,
        "capture_plan": render_capture_plan,
        "capture": render_capture,
        "preprocess": render_preprocess,
        "reconstruct": render_reconstruct,
        "optimize": render_optimize,
        "package": render_package,
        "report": render_report,
    }

    # All pages are now implemented
    pipeline_pages: list[str] = []

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
            if next_page and st.button(
                f"Next: {page_titles.get(next_page, next_page).capitalize()}"
            ):
                st.session_state.navigate_to = next_page
                st.rerun()
    else:
        st.warning("No object selected. Please select an object from the Registry.")
        if st.button("Go to Registry", key="placeholder_go_registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()


if __name__ == "__main__":
    main()
