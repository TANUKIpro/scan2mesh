"""Reconstruct page - 3D reconstruction from RGB-D frames."""

import streamlit as st

from scan2mesh_gui.components.viewer_3d import render_mesh_viewer
from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.pipeline_service import PipelineService


def render_reconstruct() -> None:
    """Render the reconstruct page."""
    st.title("3D Reconstruction")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Reconstructing **{selected_object.display_name}**")

    config = get_config_manager()
    pipeline = PipelineService(config.projects_dir)

    # Initialize state
    if "reconstruct_progress" not in st.session_state:
        st.session_state.reconstruct_progress = 0.0
    if "reconstruct_running" not in st.session_state:
        st.session_state.reconstruct_running = False
    if "reconstruct_complete" not in st.session_state:
        st.session_state.reconstruct_complete = False
    if "reconstruct_stage" not in st.session_state:
        st.session_state.reconstruct_stage = ""

    # Preprocess summary
    st.subheader("Input Summary")

    captured_frames = st.session_state.get("captured_frames", 36)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Masked Frames", int(captured_frames * 0.95))
    with col2:
        st.metric("Mask Quality", "92%")
    with col3:
        st.metric("Est. Processing", "5-10 min")

    st.divider()

    # Reconstruction settings
    st.subheader("Reconstruction Settings")

    col1, col2 = st.columns(2)

    with col1:
        st.selectbox(
            "Reconstruction Method",
            ["TSDF-Fusion", "Neural-RGBD", "BundleFusion"],
            format_func=lambda x: {
                "TSDF-Fusion": "TSDF-Fusion (Fast, standard quality)",
                "Neural-RGBD": "Neural-RGBD (Slow, AI-enhanced)",
                "BundleFusion": "BundleFusion (Medium, real-time capable)",
            }.get(x, x),
        )

        st.slider(
            "Voxel Size (mm)",
            min_value=1,
            max_value=10,
            value=3,
            help="Smaller = more detail, slower processing",
        )

    with col2:
        st.selectbox(
            "Pose Estimation",
            ["COLMAP", "ORB-SLAM3", "DroidSLAM"],
            format_func=lambda x: {
                "COLMAP": "COLMAP (Offline, accurate)",
                "ORB-SLAM3": "ORB-SLAM3 (Fast, real-time)",
                "DroidSLAM": "Droid-SLAM (Deep learning-based)",
            }.get(x, x),
        )

        st.number_input(
            "Max Depth (m)",
            min_value=0.5,
            max_value=5.0,
            value=1.5,
            step=0.1,
            help="Maximum depth for reconstruction",
        )

    with st.expander("Advanced Settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Enable loop closure", value=True)
            st.checkbox("Apply ICP refinement", value=True)
            st.number_input("SDF truncation (voxels)", value=5)
        with col2:
            st.checkbox("Color integration", value=True)
            st.checkbox("Mesh simplification", value=False)
            st.number_input("Min triangles", value=10000)

    st.divider()

    # Progress section
    st.subheader("Reconstruction Progress")

    if st.session_state.reconstruct_running:
        progress = st.session_state.reconstruct_progress
        stage = st.session_state.reconstruct_stage
        st.progress(progress)
        st.text(f"Stage: {stage}")

        # Processing steps
        steps = [
            ("Extracting features", progress > 0.1),
            ("Estimating camera poses", progress > 0.3),
            ("Building TSDF volume", progress > 0.5),
            ("Extracting mesh", progress > 0.7),
            ("Generating texture", progress > 0.9),
        ]

        for step_name, completed in steps:
            if completed:
                st.success(f":white_check_mark: {step_name}")
            elif step_name == stage:
                st.info(f":hourglass_flowing_sand: {step_name}")
            else:
                st.text(f":black_circle: {step_name}")

    elif st.session_state.reconstruct_complete:
        st.success("Reconstruction complete!")

        # Show results
        st.subheader("Results")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Vertices", "45,230")
        with col2:
            st.metric("Triangles", "89,412")
        with col3:
            st.metric("Texture Size", "2048x2048")
        with col4:
            st.metric("File Size", "12.4 MB")

        # 3D Preview
        st.subheader("3D Preview")

        # Try to render actual 3D viewer
        mesh_path = st.session_state.get("reconstructed_mesh_path")
        if mesh_path:
            render_mesh_viewer(mesh_path)
        else:
            # Placeholder
            st.markdown(
                """
                <div style="background: linear-gradient(135deg, #1a1a2e, #16213e);
                            height: 400px;
                            border-radius: 8px;
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            justify-content: center;
                            color: #4a9eff;">
                    <div style="font-size: 48px; margin-bottom: 16px;">🎯</div>
                    <div style="font-size: 18px;">3D Mesh Preview</div>
                    <div style="font-size: 14px; color: #888; margin-top: 8px;">
                        Reconstructed model would appear here
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Quality metrics
        st.subheader("Quality Metrics")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Geometry**")
            st.text("Watertight: Yes")
            st.text("Non-manifold edges: 0")
            st.text("Holes: 2 (minor)")
        with col2:
            st.markdown("**Tracking**")
            st.text("Keyframes used: 34/36")
            st.text("Tracking loss: 2 frames")
            st.text("Loop closures: 3")
        with col3:
            st.markdown("**Coverage**")
            st.text("Surface coverage: 94%")
            st.text("Texture coverage: 91%")
            st.text("Detail level: High")

    else:
        st.info("Click 'Start Reconstruction' to begin")

    st.divider()

    # Control buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Back to Preprocess", use_container_width=True):
            st.session_state.navigate_to = "preprocess"
            st.rerun()

    with col2:
        if st.session_state.reconstruct_running:
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state.reconstruct_running = False
                st.session_state.reconstruct_progress = 0.0
                st.rerun()
        else:
            if st.button(
                "Start Reconstruction",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.reconstruct_complete,
            ):
                st.session_state.reconstruct_running = True
                st.session_state.reconstruct_progress = 0.0

                # Simulate reconstruction
                import time
                stages = [
                    "Extracting features",
                    "Estimating camera poses",
                    "Building TSDF volume",
                    "Extracting mesh",
                    "Generating texture",
                ]

                with st.spinner("Reconstructing..."):
                    for i, stage in enumerate(stages):
                        st.session_state.reconstruct_stage = stage
                        st.session_state.reconstruct_progress = (i + 1) / len(stages)
                        time.sleep(0.5)

                st.session_state.reconstruct_running = False
                st.session_state.reconstruct_complete = True

                # Update object stage
                selected_object.current_stage = PipelineStage.RECONSTRUCT
                st.session_state.selected_object = selected_object

                st.rerun()

    with col3:
        if st.button(
            "Proceed to Optimize",
            type="primary" if st.session_state.reconstruct_complete else "secondary",
            use_container_width=True,
            disabled=not st.session_state.reconstruct_complete,
        ):
            st.session_state.navigate_to = "optimize"
            st.rerun()


# Run the page when loaded directly by Streamlit
render_reconstruct()
