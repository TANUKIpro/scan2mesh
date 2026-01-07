"""Devices page - manage RealSense cameras."""

import time

import streamlit as st

from scan2mesh_gui.components.camera_preview import render_camera_preview
from scan2mesh_gui.models.device import DeviceInfo
from scan2mesh_gui.services.device_service import DeviceService


def render_devices() -> None:
    """Render the devices management page."""
    st.title("Devices")
    st.markdown("Manage connected RealSense cameras")

    service = DeviceService()

    # Control bar: Refresh and Auto-refresh
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("Refresh Devices", use_container_width=True):
            st.rerun()

    with col2:
        auto_refresh = st.checkbox(
            "Auto-refresh",
            value=st.session_state.get("auto_refresh_enabled", False),
            key="auto_refresh_checkbox",
        )
        st.session_state.auto_refresh_enabled = auto_refresh

    with col3:
        # Show selected device info
        selected_device = service.get_selected_device()
        if selected_device:
            st.info(f"Selected: {selected_device.name}")
        else:
            st.caption("No device selected")

    st.divider()

    # Fetch devices
    devices = service.list_devices()

    # Update session state
    st.session_state.realsense_connected = len(devices) > 0
    if devices:
        st.session_state.realsense_device = devices[0]

    if not devices:
        st.warning("No RealSense cameras detected")
        st.markdown("""
        **Troubleshooting:**
        1. Ensure the camera is connected via USB 3.0
        2. Check that the camera is powered on
        3. Verify USB permissions (Linux: add udev rules)
        4. Try a different USB port
        """)
        return

    st.success(f"Found {len(devices)} device(s)")

    # Render device cards
    for device in devices:
        render_device_card(device, service)

    # Auto-refresh logic
    if st.session_state.get("auto_refresh_enabled", False):
        # Display countdown
        placeholder = st.empty()
        for i in range(5, 0, -1):
            placeholder.caption(f"Auto-refresh in {i} seconds...")
            time.sleep(1)
        placeholder.empty()
        st.rerun()


def render_device_card(device: DeviceInfo, service: DeviceService) -> None:
    """Render a device information card in profiles.py style."""
    serial = device.serial_number
    is_selected = service.get_selected_serial() == serial
    is_editing = st.session_state.get(f"editing_device_{serial}", False)

    # Editing mode
    if is_editing:
        render_settings_form(device, service)
        st.divider()
        return

    with st.container():
        # Header row: Device name and status
        header_col1, header_col2 = st.columns([3, 1])

        with header_col1:
            # Device name with selection indicator
            if is_selected:
                st.markdown(f"**{device.name}** :white_check_mark:")
            else:
                st.markdown(f"**{device.name}**")

            # Device info tags
            tags = [
                f"Serial: {serial}",
                f"FW: {device.firmware_version}",
                f"USB {device.usb_type}",
            ]
            tags_html = " ".join(
                f'<span style="background: #e9ecef; padding: 2px 8px; '
                f'border-radius: 4px; font-size: 12px; margin-right: 4px;">{tag}</span>'
                for tag in tags
            )
            st.markdown(tags_html, unsafe_allow_html=True)

        with header_col2:
            # Connection status
            if device.is_connected:
                st.markdown(
                    '<span style="color: #28a745;">● Connected</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span style="color: #dc3545;">○ Disconnected</span>',
                    unsafe_allow_html=True,
                )

        # Current settings row
        settings_col1, settings_col2, settings_col3 = st.columns(3)

        with settings_col1:
            if device.current_color_resolution:
                st.caption(
                    f"Color: {device.current_color_resolution[0]}x"
                    f"{device.current_color_resolution[1]}"
                )

        with settings_col2:
            if device.current_depth_resolution:
                st.caption(
                    f"Depth: {device.current_depth_resolution[0]}x"
                    f"{device.current_depth_resolution[1]}"
                )

        with settings_col3:
            st.caption(f"FPS: {device.current_fps}")

        # Action buttons row
        action_col1, action_col2, action_col3, action_col4 = st.columns(4)

        with action_col1:
            if is_selected:
                st.success("In Use", icon=":material/check:")
            elif st.button("Use this device", key=f"select_{serial}"):
                service.select_device(serial)
                st.rerun()

        with action_col2:
            if st.button("Settings", key=f"edit_{serial}"):
                st.session_state[f"editing_device_{serial}"] = True
                st.rerun()

        with action_col3:
            if st.button("Test Capture", key=f"test_{serial}"):
                with st.spinner("Capturing..."):
                    result = service.test_capture(serial)
                    if result:
                        rgb, depth = result
                        st.session_state[f"test_frame_{serial}"] = (rgb, depth)
                    else:
                        st.error("Failed to capture test frame")
                st.rerun()

        with action_col4:
            # Clear test frame button
            if st.session_state.get(f"test_frame_{serial}") and st.button(
                "Clear Preview", key=f"clear_{serial}"
            ):
                del st.session_state[f"test_frame_{serial}"]
                st.rerun()

        # Display test frame if available
        test_frame = st.session_state.get(f"test_frame_{serial}")
        if test_frame:
            rgb, depth = test_frame
            render_camera_preview(rgb, depth)

        st.divider()


def render_settings_form(device: DeviceInfo, service: DeviceService) -> None:
    """Render the settings form for a device."""
    serial = device.serial_number

    st.subheader(f"Settings: {device.name}")

    with st.form(f"settings_form_{serial}"):
        col1, col2, col3 = st.columns(3)

        with col1:
            # Color resolution
            color_options = (
                [f"{w}x{h}" for w, h in device.color_resolutions]
                if device.color_resolutions
                else ["1920x1080"]
            )
            current_color = (
                f"{device.current_color_resolution[0]}x"
                f"{device.current_color_resolution[1]}"
                if device.current_color_resolution
                else color_options[0]
            )
            color_res = st.selectbox(
                "Color Resolution",
                color_options,
                index=(
                    color_options.index(current_color)
                    if current_color in color_options
                    else 0
                ),
            )

        with col2:
            # Depth resolution
            depth_options = (
                [f"{w}x{h}" for w, h in device.depth_resolutions]
                if device.depth_resolutions
                else ["1280x720"]
            )
            current_depth = (
                f"{device.current_depth_resolution[0]}x"
                f"{device.current_depth_resolution[1]}"
                if device.current_depth_resolution
                else depth_options[0]
            )
            depth_res = st.selectbox(
                "Depth Resolution",
                depth_options,
                index=(
                    depth_options.index(current_depth)
                    if current_depth in depth_options
                    else 0
                ),
            )

        with col3:
            # FPS
            fps_options = [15, 30, 60]
            current_fps_index = (
                fps_options.index(device.current_fps)
                if device.current_fps in fps_options
                else 1
            )
            fps = st.selectbox("FPS", fps_options, index=current_fps_index)

        # Form buttons
        button_col1, button_col2 = st.columns(2)

        with button_col1:
            submitted = st.form_submit_button(
                "Apply Settings", use_container_width=True
            )

        with button_col2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)

        if submitted:
            # Parse resolution strings
            color_w, color_h = map(int, color_res.split("x"))
            depth_w, depth_h = map(int, depth_res.split("x"))

            success = service.set_resolution(
                serial,
                (color_w, color_h),
                (depth_w, depth_h),
                fps,
            )

            if success:
                st.success("Settings applied successfully!")
                st.session_state[f"editing_device_{serial}"] = False
                st.rerun()
            else:
                st.error("Failed to apply settings")

        if cancelled:
            st.session_state[f"editing_device_{serial}"] = False
            st.rerun()
