"""Components for displaying metrics and quality information."""

from typing import Any

import streamlit as st

from scan2mesh_gui.models.scan_object import QualityStatus


# Color definitions
COLORS = {
    QualityStatus.PASS: "#28a745",
    QualityStatus.WARN: "#ffc107",
    QualityStatus.FAIL: "#dc3545",
    QualityStatus.PENDING: "#6c757d",
}

LABELS = {
    QualityStatus.PASS: "PASS",
    QualityStatus.WARN: "WARN",
    QualityStatus.FAIL: "FAIL",
    QualityStatus.PENDING: "PENDING",
}


def render_quality_badge(status: QualityStatus, size: str = "medium") -> None:
    """Render a quality status badge.

    Args:
        status: The quality status to display
        size: Badge size - "small", "medium", or "large"
    """
    color = COLORS[status]
    label = LABELS[status]

    font_sizes = {"small": "12px", "medium": "16px", "large": "24px"}
    paddings = {"small": "2px 8px", "medium": "4px 12px", "large": "8px 20px"}

    font_size = font_sizes.get(size, "16px")
    padding = paddings.get(size, "4px 12px")

    st.markdown(
        f"""
        <span style="
            background-color: {color};
            color: white;
            padding: {padding};
            border-radius: 4px;
            font-size: {font_size};
            font-weight: bold;
        ">{label}</span>
        """,
        unsafe_allow_html=True,
    )


def render_metrics_table(
    metrics: dict[str, Any],
    thresholds: dict[str, tuple[float, float]] | None = None,
) -> None:
    """Render a metrics table with status indicators.

    Args:
        metrics: Dictionary of metric name -> value
        thresholds: Optional dictionary of metric name -> (warn_threshold, fail_threshold)
    """
    if not metrics:
        st.info("No metrics available")
        return

    # Build table data
    rows = []
    for name, value in metrics.items():
        # Determine status if thresholds provided
        status_icon = ""
        if thresholds and name in thresholds:
            warn_thresh, fail_thresh = thresholds[name]
            if isinstance(value, (int, float)):
                if value < fail_thresh:
                    status_icon = f'<span style="color: {COLORS[QualityStatus.FAIL]};">✗</span>'
                elif value < warn_thresh:
                    status_icon = f'<span style="color: {COLORS[QualityStatus.WARN]};">⚠</span>'
                else:
                    status_icon = f'<span style="color: {COLORS[QualityStatus.PASS]};">✓</span>'

        # Format value
        if isinstance(value, float):
            formatted_value = f"{value:.2f}"
        else:
            formatted_value = str(value)

        rows.append(f"<tr><td>{name}</td><td>{formatted_value}</td><td>{status_icon}</td></tr>")

    # Render table
    st.markdown(
        f"""
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="border-bottom: 2px solid #dee2e6;">
                    <th style="text-align: left; padding: 8px;">Metric</th>
                    <th style="text-align: right; padding: 8px;">Value</th>
                    <th style="text-align: center; padding: 8px;">Status</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def render_progress_bar(
    progress: float,
    label: str = "",
    show_percentage: bool = True,
) -> None:
    """Render a progress bar with optional label.

    Args:
        progress: Progress value between 0.0 and 1.0
        label: Optional label to display
        show_percentage: Whether to show percentage text
    """
    progress = max(0.0, min(1.0, progress))
    percentage = int(progress * 100)

    # Determine color based on progress
    if progress < 0.3:
        color = COLORS[QualityStatus.FAIL]
    elif progress < 0.7:
        color = COLORS[QualityStatus.WARN]
    else:
        color = COLORS[QualityStatus.PASS]

    text = f"{percentage}%" if show_percentage else ""

    if label:
        st.markdown(f"**{label}**")

    st.markdown(
        f"""
        <div style="
            width: 100%;
            background-color: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
        ">
            <div style="
                width: {percentage}%;
                background-color: {color};
                padding: 4px 8px;
                color: white;
                font-size: 12px;
                text-align: right;
                min-width: 30px;
            ">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(
    title: str,
    value: str | int | float,
    status: QualityStatus | None = None,
    delta: str | None = None,
) -> None:
    """Render a metric card.

    Args:
        title: Card title
        value: Main value to display
        status: Optional quality status for coloring
        delta: Optional delta/change indicator
    """
    color = COLORS.get(status, "#333") if status else "#333"
    bg_color = f"{color}10" if status else "#f8f9fa"

    st.markdown(
        f"""
        <div style="
            background-color: {bg_color};
            border: 1px solid {color if status else '#dee2e6'};
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        ">
            <p style="color: #6c757d; margin: 0; font-size: 14px;">{title}</p>
            <p style="color: {color}; margin: 8px 0 0 0; font-size: 28px; font-weight: bold;">
                {value}
            </p>
            {f'<p style="color: #6c757d; margin: 4px 0 0 0; font-size: 12px;">{delta}</p>' if delta else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
