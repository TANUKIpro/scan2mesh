"""Report page - quality report and final status."""

import json

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.report_session import ActionPriority, ReportSession
from scan2mesh_gui.models.scan_object import PipelineStage, QualityStatus
from scan2mesh_gui.services.report_service import ReportService


def render_report() -> None:
    """Render the quality report page."""
    st.title("Quality Report")

    # Check for selected object
    selected_object = st.session_state.get("selected_object")
    if not selected_object:
        st.warning("Please select an object first")
        if st.button("Go to Registry", key="report_go_registry"):
            st.session_state.navigate_to = "registry"
            st.rerun()
        return

    st.markdown(f"Quality report for **{selected_object.display_name}**")

    # Initialize service and generate report
    config = get_config_manager()
    report_service = ReportService(config.config.quality_thresholds)

    # Get sessions from session_state
    capture_session = st.session_state.get("capture_session")
    preprocess_session = st.session_state.get("preprocess_session")
    reconstruct_session = st.session_state.get("reconstruct_session")
    optimize_session = st.session_state.get("optimize_session")
    package_session = st.session_state.get("package_session")

    # Generate report
    report = report_service.generate_report(
        scan_object=selected_object,
        capture_session=capture_session,
        preprocess_session=preprocess_session,
        reconstruct_session=reconstruct_session,
        optimize_session=optimize_session,
        package_session=package_session,
    )

    # Store report in session state
    st.session_state.report_session = report

    # Render overall status banner
    _render_status_banner(report)

    st.divider()

    # Render capture metrics
    if report.capture_metrics:
        _render_capture_metrics(report, config.config.quality_thresholds)
        st.divider()

    # Render preprocess metrics
    if report.preprocess_metrics:
        _render_preprocess_metrics(report)
        st.divider()

    # Render reconstruction metrics
    if report.reconstruct_metrics:
        _render_reconstruction_metrics(report)
        st.divider()

    # Render optimization metrics
    if report.optimize_metrics:
        _render_optimization_metrics(report)
        st.divider()

    # Render package metrics
    if report.package_metrics:
        _render_package_metrics(report)
        st.divider()

    # Render quality gates
    _render_quality_gates(report)
    st.divider()

    # Render recommendations if any
    if report.recommendations:
        _render_recommendations(report)
        st.divider()

    # Export options
    _render_export_options(report)
    st.divider()

    # Action buttons
    _render_action_buttons(selected_object, report)


def _render_status_banner(report: ReportSession) -> None:
    """Render the overall status banner."""
    status_colors = {
        QualityStatus.PASS: ("#28a745", "PASS"),
        QualityStatus.WARN: ("#ffc107", "WARN"),
        QualityStatus.FAIL: ("#dc3545", "FAIL"),
        QualityStatus.PENDING: ("#6c757d", "PENDING"),
    }

    color, label = status_colors[report.overall_status]
    icon = (
        "✓" if report.overall_status == QualityStatus.PASS
        else "⚠" if report.overall_status == QualityStatus.WARN
        else "✗" if report.overall_status == QualityStatus.FAIL
        else "..."
    )

    st.markdown(
        f"""
        <div style="background: {color}22; border: 2px solid {color}; border-radius: 8px; padding: 24px; text-align: center; margin-bottom: 24px;">
            <div style="font-size: 36px; font-weight: bold; color: {color};">
                {icon} {label}
            </div>
            <div style="font-size: 16px; color: {color}; margin-top: 8px;">
                {report.status_message}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_capture_metrics(report: ReportSession, thresholds: object) -> None:
    """Render capture metrics section."""
    st.subheader("Capture Metrics")

    if report.capture_metrics is None:
        st.info("No capture metrics available")
        return

    metrics = report.capture_metrics

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Keyframes", metrics.num_keyframes)
        st.caption(f"Threshold: >= {thresholds.min_keyframes}")  # type: ignore
        _render_status_indicator(
            metrics.num_keyframes >= thresholds.min_keyframes  # type: ignore
        )

    with col2:
        st.metric("Depth Valid Ratio", f"{metrics.depth_valid_ratio:.2f}")
        st.caption(f"Threshold: >= {thresholds.depth_valid_ratio_fail}")  # type: ignore
        _render_status_indicator(
            metrics.depth_valid_ratio >= thresholds.depth_valid_ratio_fail  # type: ignore
        )

    with col3:
        st.metric("Blur Score", f"{metrics.blur_score:.2f}")
        st.caption(f"Threshold: >= {thresholds.blur_score_fail}")  # type: ignore
        _render_status_indicator(
            metrics.blur_score >= thresholds.blur_score_fail  # type: ignore
        )

    with col4:
        st.metric("Coverage", f"{metrics.coverage:.2f}")
        st.caption(f"Threshold: >= {thresholds.coverage_fail}")  # type: ignore
        _render_status_indicator(
            metrics.coverage >= thresholds.coverage_fail  # type: ignore
        )


def _render_preprocess_metrics(report: ReportSession) -> None:
    """Render preprocess metrics section."""
    st.subheader("Preprocess Metrics")

    if report.preprocess_metrics is None:
        st.info("No preprocess metrics available")
        return

    metrics = report.preprocess_metrics

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Frames Processed", metrics.num_frames_processed)

    with col2:
        st.metric("Valid Masks", metrics.num_valid_masks)

    with col3:
        st.metric("Mask Area Ratio", f"{metrics.mask_area_ratio_mean:.2f}")

    with col4:
        st.metric("Edge Quality", f"{metrics.edge_quality_mean:.2f}")


def _render_reconstruction_metrics(report: ReportSession) -> None:
    """Render reconstruction metrics section."""
    st.subheader("Reconstruction Metrics")

    if report.reconstruct_metrics is None:
        st.info("No reconstruction metrics available")
        return

    metrics = report.reconstruct_metrics

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Geometry Quality**")

        geometry_data = [
            ("Vertices", f"{metrics.num_vertices:,}", "✓"),
            ("Triangles", f"{metrics.num_triangles:,}", "✓"),
            (
                "Watertight",
                "Yes" if metrics.is_watertight else "No",
                "✓" if metrics.is_watertight else "⚠",
            ),
            ("Holes", str(metrics.num_holes), "✓" if metrics.num_holes == 0 else "⚠"),
            ("Surface Coverage", f"{metrics.surface_coverage:.2f}", "✓"),
            (
                "Texture",
                f"{metrics.texture_resolution[0]}x{metrics.texture_resolution[1]}",
                "✓",
            ),
        ]

        for name, value, status in geometry_data:
            col_a, col_b, col_c = st.columns([2, 1, 0.5])
            with col_a:
                st.text(name)
            with col_b:
                st.text(value)
            with col_c:
                st.text(status)

    with col2:
        st.markdown("**Tracking Quality**")

        tracking_data = [
            ("Keyframes Used", str(metrics.keyframes_used), "✓"),
            (
                "Tracking Loss",
                f"{metrics.tracking_loss_frames} frames",
                "✓" if metrics.tracking_loss_frames <= 3 else "⚠",
            ),
        ]

        for name, value, status in tracking_data:
            col_a, col_b, col_c = st.columns([2, 1, 0.5])
            with col_a:
                st.text(name)
            with col_b:
                st.text(value)
            with col_c:
                st.text(status)


def _render_optimization_metrics(report: ReportSession) -> None:
    """Render optimization metrics section."""
    st.subheader("Asset Metrics")

    if report.optimize_metrics is None:
        st.info("No optimization metrics available")
        return

    metrics = report.optimize_metrics

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("**LOD0 (High)**")
        st.text(f"Triangles: {metrics.lod0_triangles:,}")
        tex = metrics.texture_resolution
        st.text(f"Texture: {tex[0]}x{tex[1]}")
        st.success("OK")

    with col2:
        st.markdown("**LOD1 (Medium)**")
        st.text(f"Triangles: {metrics.lod1_triangles:,}")
        st.success("OK")

    with col3:
        st.markdown("**LOD2 (Low)**")
        st.text(f"Triangles: {metrics.lod2_triangles:,}")
        st.success("OK")

    with col4:
        st.markdown("**Collision Mesh**")
        st.text(f"Triangles: {metrics.collision_triangles:,}")
        st.success("OK")

    # Additional info
    st.markdown("**Additional Information**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text(f"Scale Factor: {metrics.scale_factor:.4f}")
    with col2:
        st.text(f"Holes Filled: {metrics.holes_filled}")
    with col3:
        bbox = metrics.bounding_box
        st.text(f"Bounding Box: {bbox[0]:.3f}m x {bbox[1]:.3f}m x {bbox[2]:.3f}m")


def _render_package_metrics(report: ReportSession) -> None:
    """Render package metrics section."""
    st.subheader("Package Metrics")

    if report.package_metrics is None:
        st.info("No package metrics available")
        return

    metrics = report.package_metrics

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Files", str(metrics.files_count))

    with col2:
        st.metric("Total Size", f"{metrics.total_size_mb:.1f} MB")

    with col3:
        if metrics.compressed_size_mb is not None:
            st.metric("Compressed", f"{metrics.compressed_size_mb:.1f} MB")
        else:
            st.metric("Compressed", "N/A")

    if metrics.output_path:
        st.markdown("**Output Path**")
        st.code(metrics.output_path)


def _render_quality_gates(report: ReportSession) -> None:
    """Render quality gate results section."""
    st.subheader("Quality Gate Results")

    if not report.quality_gates:
        st.info("No quality gates evaluated")
        return

    for gate in report.quality_gates:
        col1, col2, col3 = st.columns([2, 0.5, 3])
        with col1:
            st.text(gate.gate_name)
        with col2:
            if gate.status == QualityStatus.PASS:
                st.success("PASS")
            elif gate.status == QualityStatus.WARN:
                st.warning("WARN")
            elif gate.status == QualityStatus.FAIL:
                st.error("FAIL")
            else:
                st.info("PENDING")
        with col3:
            st.caption(gate.reason)


def _render_recommendations(report: ReportSession) -> None:
    """Render recommended actions section."""
    st.subheader("Recommended Actions")

    if not report.recommendations:
        st.info("No recommended actions")
        return

    # Sort by priority
    sorted_recs = sorted(
        report.recommendations,
        key=lambda r: (
            0 if r.priority == ActionPriority.HIGH
            else 1 if r.priority == ActionPriority.MEDIUM
            else 2
        ),
    )

    for rec in sorted_recs:
        priority_color = (
            "#dc3545" if rec.priority == ActionPriority.HIGH
            else "#ffc107" if rec.priority == ActionPriority.MEDIUM
            else "#6c757d"
        )
        priority_label = rec.priority.value.upper()

        st.markdown(
            f"""
            <div style="padding: 8px 12px; margin-bottom: 8px; border-left: 4px solid {priority_color}; background-color: {priority_color}11;">
                <strong>[{priority_label}]</strong> <em>{rec.target_stage}</em>: {rec.action}
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_export_options(report: ReportSession) -> None:
    """Render export options section."""
    st.subheader("Export Report")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Markdown export
        markdown_content = report.to_markdown()
        st.download_button(
            "Export as Markdown",
            data=markdown_content,
            file_name=f"{report.object_name}_quality_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col2:
        # JSON export
        json_content = json.dumps(report.to_json_dict(), indent=2)
        st.download_button(
            "Export as JSON",
            data=json_content,
            file_name=f"{report.object_name}_quality_report.json",
            mime="application/json",
            use_container_width=True,
        )

    with col3:
        # PDF export placeholder
        st.download_button(
            "Export as PDF (Markdown)",
            data=markdown_content,
            file_name=f"{report.object_name}_quality_report.md",
            mime="text/markdown",
            use_container_width=True,
            help="PDF export not available. Markdown file provided as alternative.",
        )


def _render_action_buttons(selected_object: object, report: ReportSession) -> None:
    """Render action buttons at the bottom."""
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Back to Package", use_container_width=True):
            st.session_state.navigate_to = "package"
            st.rerun()

    with col2:
        if st.button("Re-scan Object", type="secondary", use_container_width=True):
            # Reset pipeline state
            st.session_state.capture_session = None
            st.session_state.preprocess_session = None
            st.session_state.reconstruct_session = None
            st.session_state.optimize_session = None
            st.session_state.package_session = None
            st.session_state.report_session = None

            selected_object.current_stage = PipelineStage.INIT  # type: ignore
            st.session_state.selected_object = selected_object

            st.session_state.navigate_to = "capture_plan"
            st.rerun()

    with col3:
        if st.button("Complete & Return", type="primary", use_container_width=True):
            # Update object status
            selected_object.current_stage = PipelineStage.REPORT  # type: ignore
            selected_object.quality_status = report.overall_status  # type: ignore
            st.session_state.selected_object = selected_object

            st.success("Pipeline complete!")
            st.session_state.navigate_to = "registry"
            st.rerun()


def _render_status_indicator(is_pass: bool) -> None:
    """Render a simple pass/fail indicator."""
    if is_pass:
        st.success("PASS")
    else:
        st.error("FAIL")
