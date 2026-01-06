"""Devices page - manage RealSense cameras."""

import streamlit as st

from scan2mesh_gui.components.camera_preview import render_camera_preview
from scan2mesh_gui.services.device_service import DeviceService


def render_devices() -> None:
    """Render the devices management page."""
    st.title("Devices")
    st.markdown("Manage connected RealSense cameras")

    service = DeviceService()

    # Refresh button
    if st.button("Refresh Devices"):
        st.rerun()

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

    for device in devices:
        render_device_card(device, service)


def render_device_card(device: object, service: DeviceService) -> None:
    """Render a device information card."""
    # Type hint for IDE
    from scan2mesh_gui.models.device import DeviceInfo
    dev: DeviceInfo = device  # type: ignore

    with st.container():
        st.subheader(dev.name)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Device Information**")
            st.text(f"Serial Number: {dev.serial_number}")
            st.text(f"Firmware: {dev.firmware_version}")
            st.text(f"USB Type: {dev.usb_type}")

            # Connection status
            if dev.is_connected:
                st.success("Connected")
            else:
                st.error("Disconnected")

        with col2:
            st.markdown("**Current Settings**")

            if dev.current_color_resolution:
                st.text(f"Color: {dev.current_color_resolution[0]}x{dev.current_color_resolution[1]}")
            if dev.current_depth_resolution:
                st.text(f"Depth: {dev.current_depth_resolution[0]}x{dev.current_depth_resolution[1]}")
            st.text(f"FPS: {dev.current_fps}")

        # Resolution settings
        st.markdown("**Settings**")

        col3, col4, col5 = st.columns(3)

        with col3:
            color_options = [f"{w}x{h}" for w, h in dev.color_resolutions] if dev.color_resolutions else ["1920x1080"]
            current_color = f"{dev.current_color_resolution[0]}x{dev.current_color_resolution[1]}" if dev.current_color_resolution else color_options[0]
            color_res = st.selectbox(
                "Color Resolution",
                color_options,
                index=color_options.index(current_color) if current_color in color_options else 0,
                key=f"color_res_{dev.serial_number}",
            )

        with col4:
            depth_options = [f"{w}x{h}" for w, h in dev.depth_resolutions] if dev.depth_resolutions else ["1280x720"]
            current_depth = f"{dev.current_depth_resolution[0]}x{dev.current_depth_resolution[1]}" if dev.current_depth_resolution else depth_options[0]
            depth_res = st.selectbox(
                "Depth Resolution",
                depth_options,
                index=depth_options.index(current_depth) if current_depth in depth_options else 0,
                key=f"depth_res_{dev.serial_number}",
            )

        with col5:
            fps = st.selectbox(
                "FPS",
                [15, 30, 60],
                index=1,
                key=f"fps_{dev.serial_number}",
            )

        # Test capture
        st.markdown("**Test Capture**")

        if st.button("Capture Test Frame", key=f"test_{dev.serial_number}"):
            with st.spinner("Capturing..."):
                result = service.test_capture(dev.serial_number)
                if result:
                    rgb, depth = result
                    st.session_state[f"test_frame_{dev.serial_number}"] = (rgb, depth)
                else:
                    st.error("Failed to capture test frame")

        # Display test frame
        test_frame = st.session_state.get(f"test_frame_{dev.serial_number}")
        if test_frame:
            rgb, depth = test_frame
            render_camera_preview(rgb, depth)

        st.divider()


# Run the page when loaded directly by Streamlit
render_devices()
