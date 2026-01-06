"""Report page - quality report and final status."""

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.scan_object import PipelineStage, QualityStatus


def render_report() -> None:
    """Render the quality report page."""
    st.title("Quality Report")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Quality report for **{selected_object.display_name}**")

    config = get_config_manager()
    thresholds = config.config.quality_thresholds

    # Overall status banner
    overall_status = QualityStatus.PASS  # Simulated

    status_colors = {
        QualityStatus.PASS: ("#28a745", "Asset is ready for distribution"),
        QualityStatus.WARN: ("#ffc107", "Asset has minor issues but is usable"),
        QualityStatus.FAIL: ("#dc3545", "Asset requires re-scanning"),
        QualityStatus.PENDING: ("#6c757d", "Quality evaluation pending"),
    }

    color, message = status_colors[overall_status]

    st.markdown(
        f"""
        <div style="background: {color}22; border: 2px solid {color}; border-radius: 8px; padding: 24px; text-align: center; margin-bottom: 24px;">
            <div style="font-size: 36px; font-weight: bold; color: {color};">
                {"✓ PASS" if overall_status == QualityStatus.PASS else "⚠ WARN" if overall_status == QualityStatus.WARN else "✗ FAIL" if overall_status == QualityStatus.FAIL else "... PENDING"}
            </div>
            <div style="font-size: 16px; color: {color}; margin-top: 8px;">
                {message}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Capture metrics
    st.subheader("Capture Metrics")

    captured_frames = st.session_state.get("captured_frames", 36)

    metrics_data = [
        ("Keyframes", captured_frames, f">= {thresholds.min_keyframes}", captured_frames >= thresholds.min_keyframes),
        ("Depth Valid Ratio", 0.85, f">= {thresholds.depth_valid_ratio_fail}", thresholds.depth_valid_ratio_fail <= 0.85),
        ("Blur Score", 0.78, f">= {thresholds.blur_score_fail}", thresholds.blur_score_fail <= 0.78),
        ("Coverage", 0.92, f">= {thresholds.coverage_fail}", thresholds.coverage_fail <= 0.92),
    ]

    col1, col2, col3, col4 = st.columns(4)
    columns = [col1, col2, col3, col4]

    for i, (name, value, threshold, passed) in enumerate(metrics_data):
        with columns[i]:
            if isinstance(value, float):
                st.metric(name, f"{value:.2f}")
            else:
                st.metric(name, str(value))
            st.caption(f"Threshold: {threshold}")
            if passed:
                st.success("PASS")
            else:
                st.error("FAIL")

    st.divider()

    # Reconstruction metrics
    st.subheader("Reconstruction Metrics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Geometry Quality**")

        geometry_metrics = [
            ("Vertices", "45,230", "✓"),
            ("Triangles", "89,412", "✓"),
            ("Watertight", "Yes", "✓"),
            ("Non-manifold Edges", "0", "✓"),
            ("Holes", "2 (filled)", "⚠"),
            ("Isolated Components", "0", "✓"),
        ]

        for name, value, status in geometry_metrics:
            col_a, col_b, col_c = st.columns([2, 1, 0.5])
            with col_a:
                st.text(name)
            with col_b:
                st.text(value)
            with col_c:
                st.text(status)

    with col2:
        st.markdown("**Tracking Quality**")

        tracking_metrics = [
            ("Frames Processed", f"{captured_frames}", "✓"),
            ("Frames Used", f"{int(captured_frames * 0.95)}", "✓"),
            ("Tracking Loss", "2 frames", "⚠"),
            ("Loop Closures", "3", "✓"),
            ("Reprojection Error", "0.42 px", "✓"),
            ("Scale Accuracy", "99.2%", "✓"),
        ]

        for name, value, status in tracking_metrics:
            col_a, col_b, col_c = st.columns([2, 1, 0.5])
            with col_a:
                st.text(name)
            with col_b:
                st.text(value)
            with col_c:
                st.text(status)

    st.divider()

    # Asset metrics
    st.subheader("Asset Metrics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**LOD0 (High)**")
        st.text("Triangles: 89,412")
        st.text("Size: 8.9 MB")
        st.text("Texture: 2048x2048")
        st.success("OK")

    with col2:
        st.markdown("**LOD1 (Medium)**")
        st.text("Triangles: 30,000")
        st.text("Size: 3.2 MB")
        st.text("Texture: 1024x1024")
        st.success("OK")

    with col3:
        st.markdown("**LOD2 (Low)**")
        st.text("Triangles: 10,000")
        st.text("Size: 1.1 MB")
        st.text("Texture: 512x512")
        st.success("OK")

    st.divider()

    # Quality gate results
    st.subheader("Quality Gate Results")

    gates = [
        ("Capture Quality Gate", True, "All capture metrics meet requirements"),
        ("Geometry Quality Gate", True, "Mesh is valid and clean"),
        ("Texture Quality Gate", True, "Texture coverage and resolution adequate"),
        ("Scale Calibration Gate", True, "Scale factor applied correctly"),
        ("Asset Package Gate", True, "All required files present"),
    ]

    for gate_name, passed, reason in gates:
        col1, col2, col3 = st.columns([2, 0.5, 3])
        with col1:
            st.text(gate_name)
        with col2:
            if passed:
                st.success("PASS")
            else:
                st.error("FAIL")
        with col3:
            st.caption(reason)

    st.divider()

    # Export options
    st.subheader("Export Report")

    col1, col2, col3 = st.columns(3)

    with col1:
        # PDF export (simulated)
        st.download_button(
            "Export as PDF",
            data=f"# Quality Report for {selected_object.display_name}\n\nStatus: PASS\n\nGenerated by scan2mesh GUI",
            file_name=f"{selected_object.name}_quality_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with col2:
        # Markdown export
        report_md = f"""# Quality Report: {selected_object.display_name}

## Overall Status: PASS

## Capture Metrics
- Keyframes: {captured_frames}
- Depth Valid Ratio: 0.85
- Blur Score: 0.78
- Coverage: 0.92

## Reconstruction Metrics
- Vertices: 45,230
- Triangles: 89,412
- Watertight: Yes

## Asset Output
- LOD0: 89,412 triangles
- LOD1: 30,000 triangles
- LOD2: 10,000 triangles

---
Generated by scan2mesh GUI
"""
        st.download_button(
            "Export as Markdown",
            data=report_md,
            file_name=f"{selected_object.name}_quality_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col3:
        # JSON export
        import json
        report_json = {
            "object_name": selected_object.name,
            "display_name": selected_object.display_name,
            "status": "PASS",
            "capture_metrics": {
                "keyframes": captured_frames,
                "depth_valid_ratio": 0.85,
                "blur_score": 0.78,
                "coverage": 0.92,
            },
            "reconstruction_metrics": {
                "vertices": 45230,
                "triangles": 89412,
                "watertight": True,
            },
        }
        st.download_button(
            "Export as JSON",
            data=json.dumps(report_json, indent=2),
            file_name=f"{selected_object.name}_quality_report.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Back to Package", use_container_width=True):
            st.session_state.navigate_to = "package"
            st.rerun()

    with col2:
        if st.button("Re-scan Object", type="secondary", use_container_width=True):
            # Reset pipeline state
            st.session_state.captured_frames = 0
            st.session_state.capture_metrics = {}
            st.session_state.preprocess_complete = False
            st.session_state.reconstruct_complete = False
            st.session_state.optimize_complete = False
            st.session_state.package_complete = False

            selected_object.current_stage = PipelineStage.INIT
            st.session_state.selected_object = selected_object

            st.session_state.navigate_to = "capture_plan"
            st.rerun()

    with col3:
        if st.button("Complete & Return", type="primary", use_container_width=True):
            # Update object status
            selected_object.current_stage = PipelineStage.REPORT
            selected_object.quality_status = overall_status
            st.session_state.selected_object = selected_object

            st.success("Pipeline complete!")
            st.session_state.navigate_to = "registry"
            st.rerun()


# Run the page when loaded directly by Streamlit
render_report()
