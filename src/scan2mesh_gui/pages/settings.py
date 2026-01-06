"""Settings page - application configuration."""

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.config import AppConfig


def render_settings() -> None:
    """Render the settings page."""
    st.title("Settings")
    st.markdown("Configure application settings")

    config_manager = get_config_manager()
    config = config_manager.config

    # Output preset settings
    st.subheader("Output Preset")

    col1, col2 = st.columns(2)

    with col1:
        coordinate_system = st.selectbox(
            "Coordinate System",
            ["Z-up", "Y-up"],
            index=0 if config.default_preset.coordinate_system == "Z-up" else 1,
        )

        units = st.selectbox(
            "Units",
            ["meter", "millimeter"],
            index=0 if config.default_preset.units == "meter" else 1,
        )

    with col2:
        texture_resolution = st.selectbox(
            "Texture Resolution",
            [512, 1024, 2048, 4096],
            index=[512, 1024, 2048, 4096].index(config.default_preset.texture_resolution),
        )

        lod_limits = st.text_input(
            "LOD Triangle Limits",
            value=", ".join(str(x) for x in config.default_preset.lod_triangle_limits),
            help="Comma-separated values for LOD0, LOD1, LOD2",
        )

    st.divider()

    # Quality thresholds
    st.subheader("Quality Thresholds")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("**Depth Valid Ratio**")
        depth_warn = st.slider(
            "Warning Threshold",
            0.0, 1.0,
            config.quality_thresholds.depth_valid_ratio_warn,
            key="depth_warn",
        )
        depth_fail = st.slider(
            "Fail Threshold",
            0.0, 1.0,
            config.quality_thresholds.depth_valid_ratio_fail,
            key="depth_fail",
        )

    with col4:
        st.markdown("**Blur Score**")
        blur_warn = st.slider(
            "Warning Threshold",
            0.0, 1.0,
            config.quality_thresholds.blur_score_warn,
            key="blur_warn",
        )
        blur_fail = st.slider(
            "Fail Threshold",
            0.0, 1.0,
            config.quality_thresholds.blur_score_fail,
            key="blur_fail",
        )

    col5, col6 = st.columns(2)

    with col5:
        st.markdown("**Coverage**")
        coverage_warn = st.slider(
            "Warning Threshold",
            0.0, 1.0,
            config.quality_thresholds.coverage_warn,
            key="coverage_warn",
        )
        coverage_fail = st.slider(
            "Fail Threshold",
            0.0, 1.0,
            config.quality_thresholds.coverage_fail,
            key="coverage_fail",
        )

    with col6:
        st.markdown("**Keyframes**")
        min_keyframes = st.number_input(
            "Minimum Keyframes",
            min_value=1,
            max_value=100,
            value=config.quality_thresholds.min_keyframes,
        )

    st.divider()

    # Paths
    st.subheader("Paths")

    col7, col8 = st.columns(2)

    with col7:
        profiles_dir = st.text_input(
            "Profiles Directory",
            value=config.profiles_dir,
        )
        projects_dir = st.text_input(
            "Projects Directory",
            value=config.projects_dir,
        )

    with col8:
        output_dir = st.text_input(
            "Output Directory",
            value=config.output_dir,
        )
        log_level = st.selectbox(
            "Log Level",
            ["DEBUG", "INFO", "WARNING", "ERROR"],
            index=["DEBUG", "INFO", "WARNING", "ERROR"].index(config.log_level),
        )

    st.divider()

    # System information
    st.subheader("System Information")

    col9, col10 = st.columns(2)

    with col9:
        st.markdown("**Hardware**")
        # CPU info
        import platform
        st.text(f"Platform: {platform.system()} {platform.release()}")
        st.text(f"Python: {platform.python_version()}")

        # GPU info
        gpu_available = st.session_state.get("gpu_available", False)
        if gpu_available:
            gpu_name = st.session_state.get("gpu_name", "Unknown")
            st.text(f"GPU: {gpu_name}")
        else:
            st.text("GPU: Not available (CPU mode)")

    with col10:
        st.markdown("**Disk Space**")
        import shutil
        try:
            total, used, free = shutil.disk_usage("/")
            st.text(f"Total: {total // (1024**3)} GB")
            st.text(f"Used: {used // (1024**3)} GB")
            st.text(f"Free: {free // (1024**3)} GB")
        except Exception:
            st.text("Unable to get disk info")

    st.divider()

    # Save button
    if st.button("Save Settings", type="primary"):
        try:
            # Parse LOD limits
            lod_values = [int(x.strip()) for x in lod_limits.split(",")]
            if len(lod_values) != 3:
                st.error("LOD limits must have exactly 3 values")
                return

            # Update config
            new_config = AppConfig(
                profiles_dir=profiles_dir,
                projects_dir=projects_dir,
                output_dir=output_dir,
                log_level=log_level,
                default_preset={
                    "coordinate_system": coordinate_system,
                    "units": units,
                    "texture_resolution": texture_resolution,
                    "lod_triangle_limits": lod_values,
                },
                quality_thresholds={
                    "depth_valid_ratio_warn": depth_warn,
                    "depth_valid_ratio_fail": depth_fail,
                    "blur_score_warn": blur_warn,
                    "blur_score_fail": blur_fail,
                    "coverage_warn": coverage_warn,
                    "coverage_fail": coverage_fail,
                    "min_keyframes": min_keyframes,
                },
            )
            config_manager._config = new_config
            config_manager.save()
            st.success("Settings saved successfully!")

        except Exception as e:
            st.error(f"Failed to save settings: {e}")


# Run the page when loaded directly by Streamlit
render_settings()
