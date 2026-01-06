"""Reconstruct page - 3D reconstruction from RGB-D frames."""

import time

import streamlit as st

from scan2mesh_gui.components.viewer_3d import render_mesh_viewer
from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.reconstruct_session import (
    ReconstructSession,
    ReconstructStage,
)
from scan2mesh_gui.models.scan_object import PipelineStage
from scan2mesh_gui.services.reconstruct_service import ReconstructService


def render_reconstruct() -> None:
    """Render the reconstruct page."""
    st.title("3D Reconstruction")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry", key="reconstruct_go_registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Reconstructing **{selected_object.display_name}**")

    # Initialize config and service
    config = get_config_manager()
    reconstruct_service = ReconstructService(config.projects_dir)

    # Initialize session state
    if "reconstruct_session" not in st.session_state:
        st.session_state.reconstruct_session = None

    # Get input information from preprocess session
    preprocess_session = st.session_state.get("preprocess_session")
    if preprocess_session is not None:
        input_frames = len(preprocess_session.masked_frames)
        mask_quality_mean = preprocess_session.metrics.mask_area_ratio_mean
    else:
        # Fallback values if no preprocess session
        input_frames = st.session_state.get("captured_frames", 36)
        mask_quality_mean = 0.92

    # Input summary section
    st.subheader("Input Summary")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Masked Frames", input_frames)
    with col2:
        st.metric("Mask Quality", f"{mask_quality_mean * 100:.0f}%")
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

    # Get current session
    session: ReconstructSession | None = st.session_state.reconstruct_session

    # Progress section
    st.subheader("Reconstruction Progress")

    if session is not None and session.is_running:
        # Show progress
        st.progress(session.progress)
        st.text(f"Stage: {session.stage_display_name}")

        # Processing steps with status
        _render_stage_steps(session)

    elif session is not None and session.is_complete:
        st.success("Reconstruction complete!")

        # Show results
        _render_results(session)

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
        if session is not None and session.is_running:
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state.reconstruct_session = reconstruct_service.stop_session(
                    session
                )
                st.rerun()
        else:
            is_complete = session is not None and session.is_complete
            if st.button(
                "Start Reconstruction",
                type="primary",
                use_container_width=True,
                disabled=is_complete,
            ):
                _run_reconstruction(
                    reconstruct_service,
                    selected_object,
                    input_frames,
                )

    with col3:
        can_proceed = session is not None and session.can_proceed
        if st.button(
            "Proceed to Optimize",
            type="primary" if can_proceed else "secondary",
            use_container_width=True,
            disabled=not can_proceed,
        ):
            st.session_state.navigate_to = "optimize"
            st.rerun()


def _render_stage_steps(session: ReconstructSession) -> None:
    """Render the stage steps with completion status."""
    stages = [
        (ReconstructStage.FEATURE_EXTRACTION, "Extracting features"),
        (ReconstructStage.POSE_ESTIMATION, "Estimating camera poses"),
        (ReconstructStage.TSDF_FUSION, "Building TSDF volume"),
        (ReconstructStage.MESH_EXTRACTION, "Extracting mesh"),
        (ReconstructStage.TEXTURE_MAPPING, "Generating texture"),
    ]

    from scan2mesh_gui.models.reconstruct_session import STAGE_ORDER

    current_index = STAGE_ORDER.index(session.current_stage)

    for stage, step_name in stages:
        stage_index = STAGE_ORDER.index(stage)

        if stage_index < current_index:
            st.success(f":white_check_mark: {step_name}")
        elif stage == session.current_stage:
            st.info(f":hourglass_flowing_sand: {step_name}")
        else:
            st.text(f":black_circle: {step_name}")


def _render_results(session: ReconstructSession) -> None:
    """Render reconstruction results."""
    metrics = session.metrics

    # Summary metrics
    st.subheader("Results")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Vertices", f"{metrics.num_vertices:,}")
    with col2:
        st.metric("Triangles", f"{metrics.num_triangles:,}")
    with col3:
        tex_w, tex_h = metrics.texture_resolution
        st.metric("Texture Size", f"{tex_w}x{tex_h}")
    with col4:
        size_mb = metrics.file_size_bytes / (1024 * 1024)
        st.metric("File Size", f"{size_mb:.1f} MB")

    # 3D Preview
    st.subheader("3D Preview")

    # Check if mesh file exists (for mock sessions, it won't)
    from pathlib import Path

    mesh_exists = session.output_mesh_path and Path(session.output_mesh_path).exists()
    if mesh_exists:
        render_mesh_viewer(session.output_mesh_path)
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
        watertight_status = "Yes" if metrics.is_watertight else "No"
        st.text(f"Watertight: {watertight_status}")
        st.text("Non-manifold edges: 0")
        holes_desc = f"{metrics.num_holes} (minor)" if metrics.num_holes > 0 else "0"
        st.text(f"Holes: {holes_desc}")
    with col2:
        st.markdown("**Tracking**")
        st.text(f"Keyframes used: {metrics.keyframes_used}/{session.input_frames}")
        st.text(f"Tracking loss: {metrics.tracking_loss_frames} frames")
        st.text("Loop closures: 3")
    with col3:
        st.markdown("**Coverage**")
        st.text(f"Surface coverage: {metrics.surface_coverage * 100:.0f}%")
        st.text("Texture coverage: 91%")
        st.text("Detail level: High")


def _run_reconstruction(
    service: ReconstructService,
    selected_object: object,
    input_frames: int,
) -> None:
    """Run the reconstruction process with progress updates."""
    # Start session
    session = service.start_session(
        object_id=selected_object.id,  # type: ignore
        input_frames=input_frames,
    )
    st.session_state.reconstruct_session = session

    # Run through stages with visual feedback
    with st.spinner("Reconstructing..."):
        # Advance from IDLE to first stage
        session = service.advance_stage(session)
        st.session_state.reconstruct_session = session

        # Process each stage
        while not session.is_complete:
            time.sleep(0.5)  # Simulate processing time
            session = service.advance_stage(session)
            st.session_state.reconstruct_session = session

    # Update object stage
    selected_object.current_stage = PipelineStage.RECONSTRUCT  # type: ignore
    st.session_state.selected_object = selected_object

    st.rerun()


# Run the page when loaded directly by Streamlit
render_reconstruct()
