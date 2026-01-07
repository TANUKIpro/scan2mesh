"""Settings page - application configuration."""

import logging
import os
import platform
import shutil
import subprocess

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.config import AppConfig


logger = logging.getLogger(__name__)


def get_cpu_info() -> dict[str, str]:
    """Get CPU information.

    Returns:
        Dictionary with processor name and core count.
    """
    processor = platform.processor()
    if not processor:
        # Fallback for some platforms
        processor = platform.machine()

    core_count = os.cpu_count() or 0

    return {
        "processor": processor if processor else "Unknown",
        "cores": str(core_count),
    }


def get_memory_info() -> dict[str, str]:
    """Get memory information.

    Returns:
        Dictionary with total, used, and free memory in GB.
    """
    try:
        if platform.system() == "Darwin":
            # macOS: use sysctl
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                total_bytes = int(result.stdout.strip())
                total_gb = total_bytes / (1024**3)

                # Get used memory via vm_stat
                vm_result = subprocess.run(
                    ["vm_stat"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if vm_result.returncode == 0:
                    # Parse vm_stat output
                    lines = vm_result.stdout.strip().split("\n")
                    page_size = 4096  # Default page size
                    free_pages = 0
                    inactive_pages = 0

                    for line in lines:
                        if "page size of" in line:
                            parts = line.split()
                            for part in parts:
                                if part.isdigit():
                                    page_size = int(part)
                                    break
                        elif "Pages free:" in line:
                            free_pages = int(line.split(":")[1].strip().rstrip("."))
                        elif "Pages inactive:" in line:
                            inactive_pages = int(line.split(":")[1].strip().rstrip("."))

                    free_bytes = (free_pages + inactive_pages) * page_size
                    free_gb = free_bytes / (1024**3)
                    used_gb = total_gb - free_gb

                    return {
                        "total": f"{total_gb:.1f} GB",
                        "used": f"{used_gb:.1f} GB",
                        "free": f"{free_gb:.1f} GB",
                    }

                return {
                    "total": f"{total_gb:.1f} GB",
                    "used": "N/A",
                    "free": "N/A",
                }

        else:
            # Linux: read /proc/meminfo
            from pathlib import Path

            with Path("/proc/meminfo").open() as f:
                meminfo = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip().split()[0]
                        meminfo[key] = int(value)

                total_kb = meminfo.get("MemTotal", 0)
                free_kb = meminfo.get("MemFree", 0)
                available_kb = meminfo.get("MemAvailable", free_kb)
                used_kb = total_kb - available_kb

                return {
                    "total": f"{total_kb / (1024**2):.1f} GB",
                    "used": f"{used_kb / (1024**2):.1f} GB",
                    "free": f"{available_kb / (1024**2):.1f} GB",
                }

    except (subprocess.SubprocessError, OSError, ValueError) as e:
        logger.debug("Failed to get memory info: %s", e)

    return {
        "total": "N/A",
        "used": "N/A",
        "free": "N/A",
    }


def get_gpu_info() -> dict[str, str]:
    """Get GPU information including VRAM.

    Returns:
        Dictionary with GPU name, availability, and VRAM info.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            if len(parts) >= 4:
                name = parts[0].strip()
                total_mb = int(parts[1].strip())
                used_mb = int(parts[2].strip())
                free_mb = int(parts[3].strip())

                return {
                    "available": "true",
                    "name": name,
                    "vram_total": f"{total_mb / 1024:.1f} GB",
                    "vram_used": f"{used_mb / 1024:.1f} GB",
                    "vram_free": f"{free_mb / 1024:.1f} GB",
                }
            else:
                # Basic info only
                name = parts[0].strip() if parts else "Unknown GPU"
                return {
                    "available": "true",
                    "name": name,
                    "vram_total": "N/A",
                    "vram_used": "N/A",
                    "vram_free": "N/A",
                }
    except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
        logger.debug("Failed to get GPU info: %s", e)

    return {
        "available": "false",
        "name": "Not available (CPU mode)",
        "vram_total": "N/A",
        "vram_used": "N/A",
        "vram_free": "N/A",
    }


def get_disk_info(path: str = "/") -> dict[str, str]:
    """Get disk usage information.

    Args:
        path: Path to check disk usage for.

    Returns:
        Dictionary with total, used, and free disk space in GB.
    """
    try:
        total, used, free = shutil.disk_usage(path)
        return {
            "total": f"{total // (1024**3)} GB",
            "used": f"{used // (1024**3)} GB",
            "free": f"{free // (1024**3)} GB",
        }
    except OSError as e:
        logger.debug("Failed to get disk info: %s", e)
        return {
            "total": "N/A",
            "used": "N/A",
            "free": "N/A",
        }


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

    # Get system info
    cpu_info = get_cpu_info()
    memory_info = get_memory_info()
    gpu_info = get_gpu_info()
    disk_info = get_disk_info()

    col9, col10 = st.columns(2)

    with col9:
        st.markdown("**Platform**")
        st.text(f"OS: {platform.system()} {platform.release()}")
        st.text(f"Python: {platform.python_version()}")

        st.markdown("**CPU**")
        st.text(f"Processor: {cpu_info['processor']}")
        st.text(f"Cores: {cpu_info['cores']}")

        st.markdown("**Memory**")
        st.text(f"Total: {memory_info['total']}")
        st.text(f"Used: {memory_info['used']}")
        st.text(f"Free: {memory_info['free']}")

    with col10:
        st.markdown("**GPU**")
        if gpu_info["available"] == "true":
            st.text(f"Name: {gpu_info['name']}")
            st.text(f"VRAM Total: {gpu_info['vram_total']}")
            st.text(f"VRAM Used: {gpu_info['vram_used']}")
            st.text(f"VRAM Free: {gpu_info['vram_free']}")
        else:
            st.text(gpu_info["name"])

        st.markdown("**Disk Space**")
        st.text(f"Total: {disk_info['total']}")
        st.text(f"Used: {disk_info['used']}")
        st.text(f"Free: {disk_info['free']}")

    st.divider()

    # Config file info
    st.subheader("Configuration File")
    st.text(f"Location: {config_manager.config_path}")
    if config_manager.config_path.exists():
        st.text("Status: File exists")
    else:
        st.text("Status: Using default settings (file not created yet)")

    st.divider()

    # Action buttons
    col_save, col_reset = st.columns(2)

    with col_save:
        if st.button("Save Settings", type="primary"):
            try:
                # Parse LOD limits
                try:
                    lod_values = [int(x.strip()) for x in lod_limits.split(",")]
                except ValueError:
                    st.error("LOD limits must contain valid integers")
                    return

                if len(lod_values) != 3:
                    st.error("LOD limits must have exactly 3 values")
                    return

                if any(v <= 0 for v in lod_values):
                    st.error("LOD limits must be positive integers")
                    return

                if lod_values != sorted(lod_values, reverse=True):
                    st.error(
                        "LOD limits should be in descending order (LOD0 > LOD1 > LOD2)"
                    )
                    return

                # Validate threshold consistency
                if depth_warn <= depth_fail:
                    st.error(
                        "Depth warning threshold must be greater than fail threshold"
                    )
                    return

                if blur_warn <= blur_fail:
                    st.error(
                        "Blur warning threshold must be greater than fail threshold"
                    )
                    return

                if coverage_warn <= coverage_fail:
                    st.error(
                        "Coverage warning threshold must be greater than fail threshold"
                    )
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

    with col_reset:
        if st.button("Reset to Defaults", type="secondary"):
            st.session_state.confirm_reset = True

    # Reset confirmation dialog
    if st.session_state.get("confirm_reset", False):
        st.warning("Are you sure you want to reset all settings to defaults?")
        confirm_col1, confirm_col2 = st.columns(2)
        with confirm_col1:
            if st.button("Yes, Reset", key="confirm_reset_yes"):
                try:
                    # Create default config
                    default_config = AppConfig()
                    config_manager._config = default_config
                    config_manager.save()
                    st.session_state.confirm_reset = False
                    st.success("Settings reset to defaults!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to reset settings: {e}")
        with confirm_col2:
            if st.button("Cancel", key="confirm_reset_no"):
                st.session_state.confirm_reset = False
                st.rerun()
