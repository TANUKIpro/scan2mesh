"""Package page - export final asset bundle."""

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.pipeline_service import PipelineService


def render_package() -> None:
    """Render the package page."""
    st.title("Package")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Packaging **{selected_object.display_name}**")

    config = get_config_manager()
    pipeline = PipelineService(config.projects_dir)

    # Initialize state
    if "package_complete" not in st.session_state:
        st.session_state.package_complete = False
    if "package_path" not in st.session_state:
        st.session_state.package_path = None

    # Asset summary
    st.subheader("Asset Summary")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("LOD Levels", "3")
    with col2:
        st.metric("Total Size", "15.2 MB")
    with col3:
        st.metric("Texture Size", "2048x2048")
    with col4:
        st.metric("Has Collision", "Yes")

    st.divider()

    # Package contents preview
    st.subheader("Package Contents")

    st.markdown("""
    ```
    {object_name}/
    ├── meshes/
    │   ├── {object_name}_lod0.glb       # High detail (89,412 triangles)
    │   ├── {object_name}_lod1.glb       # Medium detail (30,000 triangles)
    │   ├── {object_name}_lod2.glb       # Low detail (10,000 triangles)
    │   └── {object_name}_collision.glb  # Collision mesh (512 triangles)
    │
    ├── textures/
    │   ├── {object_name}_albedo.png     # 2048x2048
    │   └── {object_name}_normal.png     # 2048x2048 (optional)
    │
    ├── metadata/
    │   ├── manifest.json                # Asset manifest
    │   ├── quality_report.json          # Quality metrics
    │   └── capture_info.json            # Capture parameters
    │
    └── preview/
        ├── thumbnail.png                # 256x256
        └── preview.png                  # 512x512
    ```
    """.replace("{object_name}", selected_object.name))

    st.divider()

    # Export options
    st.subheader("Export Options")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Output Format**")
        export_format = st.selectbox(
            "Format",
            ["directory", "zip"],
            format_func=lambda x: {
                "directory": "Directory (uncompressed)",
                "zip": "ZIP Archive (compressed)",
            }.get(x, x),
            label_visibility="collapsed",
        )

        st.markdown("**Include**")
        include_lod0 = st.checkbox("LOD0 (High)", value=True)
        include_lod1 = st.checkbox("LOD1 (Medium)", value=True)
        include_lod2 = st.checkbox("LOD2 (Low)", value=True)
        include_collision = st.checkbox("Collision Mesh", value=True)

    with col2:
        st.markdown("**Metadata**")
        include_manifest = st.checkbox("Manifest JSON", value=True)
        include_report = st.checkbox("Quality Report", value=True)
        include_capture_info = st.checkbox("Capture Info", value=True)
        include_preview = st.checkbox("Preview Images", value=True)

        st.markdown("**Additional**")
        include_source = st.checkbox("Source Files", value=False, help="Include original frames and masks")

    st.divider()

    # Output path
    st.subheader("Output Location")

    output_dir = st.text_input(
        "Output Directory",
        value=config.config.output_dir,
    )

    # Generate filename
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{selected_object.name}_{timestamp}"

    if export_format == "zip":
        filename += ".zip"

    st.text(f"Output: {output_dir}/{filename}")

    st.divider()

    # Results section
    if st.session_state.package_complete:
        st.subheader("Package Complete!")

        st.success(f"Asset exported to: {st.session_state.package_path}")

        # Download button (simulated)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Package",
                data=f"# Simulated package for {selected_object.name}",
                file_name=filename if export_format == "zip" else f"{filename}.txt",
                mime="application/zip" if export_format == "zip" else "text/plain",
            )
        with col2:
            if st.button("Open in Explorer"):
                st.info("Would open file explorer to package location")

        # Package stats
        st.markdown("**Package Statistics**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Files", "12")
        with col2:
            st.metric("Total Size", "15.2 MB" if not include_source else "245 MB")
        with col3:
            st.metric("Compressed", "8.7 MB" if export_format == "zip" else "N/A")
        with col4:
            st.metric("Format", "GLB + PNG")

    st.divider()

    # Control buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Back to Optimize", use_container_width=True):
            st.session_state.navigate_to = "optimize"
            st.rerun()

    with col2:
        if st.button(
            "Create Package",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.package_complete,
        ):
            with st.spinner("Creating package..."):
                import time
                time.sleep(1.5)

            # Simulate package creation
            st.session_state.package_complete = True
            st.session_state.package_path = f"{output_dir}/{filename}"

            # Update object stage
            selected_object.current_stage = PipelineStage.PACKAGE
            st.session_state.selected_object = selected_object

            st.rerun()

    with col3:
        if st.button(
            "View Report",
            type="primary" if st.session_state.package_complete else "secondary",
            use_container_width=True,
            disabled=not st.session_state.package_complete,
        ):
            st.session_state.navigate_to = "report"
            st.rerun()


# Run the page when loaded directly by Streamlit
render_package()
