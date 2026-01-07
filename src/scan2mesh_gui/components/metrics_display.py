"""Components for displaying metrics and quality information."""

from typing import Any

import streamlit as st

from scan2mesh_gui.models.scan_object import QualityStatus


# Color definitions - CSS variables for theme compatibility
COLORS = {
    QualityStatus.PASS: "var(--color-accent-success)",
    QualityStatus.WARN: "var(--color-accent-warning)",
    QualityStatus.FAIL: "var(--color-accent-danger)",
    QualityStatus.PENDING: "var(--color-text-muted)",
}

# Background colors with transparency
BG_COLORS = {
    QualityStatus.PASS: "rgba(34, 197, 94, 0.15)",
    QualityStatus.WARN: "rgba(245, 158, 11, 0.15)",
    QualityStatus.FAIL: "rgba(239, 68, 68, 0.15)",
    QualityStatus.PENDING: "rgba(148, 163, 184, 0.15)",
}

# Border colors with transparency
BORDER_COLORS = {
    QualityStatus.PASS: "rgba(34, 197, 94, 0.3)",
    QualityStatus.WARN: "rgba(245, 158, 11, 0.3)",
    QualityStatus.FAIL: "rgba(239, 68, 68, 0.3)",
    QualityStatus.PENDING: "rgba(148, 163, 184, 0.3)",
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
    bg_color = BG_COLORS[status]
    border_color = BORDER_COLORS[status]
    label = LABELS[status]

    font_sizes = {"small": "0.65rem", "medium": "0.75rem", "large": "0.875rem"}
    paddings = {"small": "0.125rem 0.5rem", "medium": "0.25rem 0.75rem", "large": "0.375rem 1rem"}

    font_size = font_sizes.get(size, "0.75rem")
    padding = paddings.get(size, "0.25rem 0.75rem")

    st.markdown(
        f"""
        <span class="precision-badge" style="
            background: {bg_color};
            color: {color};
            border: 1px solid {border_color};
            padding: {padding};
            font-size: {font_size};
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
        st.markdown(
            """
            <div style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3);
                        border-radius: 10px; padding: 1rem; text-align: center;">
                <p style="color: var(--color-text-secondary); margin: 0;">No metrics available</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
                    status_icon = '<span class="status-dot status-dot-danger"></span>'
                elif value < warn_thresh:
                    status_icon = '<span class="status-dot status-dot-warning"></span>'
                else:
                    status_icon = '<span class="status-dot status-dot-success"></span>'

        # Format value
        formatted_value = f"{value:.2f}" if isinstance(value, float) else str(value)

        rows.append(
            f"""<tr style="border-bottom: 1px solid var(--color-border);">
                <td style="padding: 0.75rem; color: var(--color-text-secondary); font-size: 0.875rem;">{name}</td>
                <td style="padding: 0.75rem; color: var(--color-text-primary); font-family: 'JetBrains Mono', monospace;
                           font-size: 0.875rem; text-align: right;">{formatted_value}</td>
                <td style="padding: 0.75rem; text-align: center;">{status_icon}</td>
            </tr>"""
        )

    # Render table
    st.markdown(
        f"""
        <div class="precision-card" style="padding: 0; overflow: hidden;">
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: var(--color-bg-tertiary); border-bottom: 1px solid var(--color-border);">
                        <th style="text-align: left; padding: 0.75rem; font-size: 0.75rem; font-weight: 600;
                                   color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Metric</th>
                        <th style="text-align: right; padding: 0.75rem; font-size: 0.75rem; font-weight: 600;
                                   color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Value</th>
                        <th style="text-align: center; padding: 0.75rem; font-size: 0.75rem; font-weight: 600;
                                   color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
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
        glow_color = "rgba(239, 68, 68, 0.3)"
    elif progress < 0.7:
        color = COLORS[QualityStatus.WARN]
        glow_color = "rgba(245, 158, 11, 0.3)"
    else:
        color = COLORS[QualityStatus.PASS]
        glow_color = "rgba(34, 197, 94, 0.3)"

    text = f"{percentage}%" if show_percentage else ""

    if label:
        st.markdown(
            f'<p style="font-size: 0.75rem; font-weight: 600; color: var(--color-text-secondary); '
            f'margin-bottom: 0.5rem;">{label}</p>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div style="
            width: 100%;
            background: var(--color-bg-secondary);
            border-radius: 9999px;
            overflow: hidden;
            height: 8px;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
        ">
            <div style="
                width: {percentage}%;
                background: linear-gradient(90deg, {color} 0%, {color}dd 100%);
                height: 100%;
                border-radius: 9999px;
                box-shadow: 0 0 10px {glow_color};
                transition: width 0.3s ease;
            "></div>
        </div>
        {f'<p style="font-family: JetBrains Mono, monospace; font-size: 0.75rem; color: var(--color-text-primary); text-align: right; margin-top: 0.25rem;">{text}</p>' if show_percentage else ''}
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
    if status:
        color = COLORS.get(status, "var(--color-text-primary)")
        border_color = BORDER_COLORS.get(status, "var(--color-border)")
        glow = f"0 0 20px {BORDER_COLORS.get(status, 'transparent')}"
    else:
        color = "var(--color-text-primary)"
        border_color = "var(--color-border)"
        glow = "none"

    st.markdown(
        f"""
        <div class="precision-card" style="
            background: linear-gradient(135deg, var(--color-bg-tertiary) 0%, var(--color-bg-secondary) 100%);
            border: 1px solid {border_color};
            border-left: 3px solid {color};
            text-align: center;
            box-shadow: {glow};
        ">
            <p style="color: var(--color-text-muted); margin: 0; font-size: 0.75rem; font-weight: 500;
                      text-transform: uppercase; letter-spacing: 0.05em;">{title}</p>
            <p style="color: {color}; margin: 0.5rem 0 0 0; font-size: 1.75rem; font-weight: 700;
                      font-family: 'JetBrains Mono', monospace; line-height: 1.2;">
                {value}
            </p>
            {f'<p style="color: var(--color-text-muted); margin: 0.25rem 0 0 0; font-size: 0.7rem;">{delta}</p>' if delta else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
