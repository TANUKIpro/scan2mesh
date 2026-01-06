"""Camera preview components for RGB and Depth display."""

from typing import Any

import numpy as np
import streamlit as st


def colorize_depth(
    depth: np.ndarray,
    min_depth: float = 0.2,
    max_depth: float = 3.0,
) -> np.ndarray:
    """Convert depth image to colorized RGB image.

    Args:
        depth: Depth image in meters or millimeters
        min_depth: Minimum depth for colorization
        max_depth: Maximum depth for colorization

    Returns:
        Colorized RGB image (uint8)
    """
    # Handle different depth formats
    if depth.dtype == np.uint16:
        # Assume millimeters, convert to meters
        depth_m = depth.astype(np.float32) / 1000.0
    else:
        depth_m = depth.astype(np.float32)

    # Clip to valid range
    depth_clipped = np.clip(depth_m, min_depth, max_depth)

    # Normalize to 0-1
    normalized = (depth_clipped - min_depth) / (max_depth - min_depth)

    # Apply colormap (turbo-like)
    # Create a simple rainbow colormap
    h = (1.0 - normalized) * 0.7  # Hue from red to blue
    s = np.ones_like(h)
    v = np.where(depth_m > 0, 1.0, 0.3)  # Dim invalid pixels

    # HSV to RGB conversion
    rgb = hsv_to_rgb(h, s, v)

    return (rgb * 255).astype(np.uint8)


def hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Convert HSV to RGB.

    Args:
        h: Hue (0-1)
        s: Saturation (0-1)
        v: Value (0-1)

    Returns:
        RGB image as float32 (0-1)
    """
    i = (h * 6.0).astype(np.int32)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    i = i % 6

    rgb = np.zeros((*h.shape, 3), dtype=np.float32)

    mask = i == 0
    rgb[mask] = np.stack([v[mask], t[mask], p[mask]], axis=-1)
    mask = i == 1
    rgb[mask] = np.stack([q[mask], v[mask], p[mask]], axis=-1)
    mask = i == 2
    rgb[mask] = np.stack([p[mask], v[mask], t[mask]], axis=-1)
    mask = i == 3
    rgb[mask] = np.stack([p[mask], q[mask], v[mask]], axis=-1)
    mask = i == 4
    rgb[mask] = np.stack([t[mask], p[mask], v[mask]], axis=-1)
    mask = i == 5
    rgb[mask] = np.stack([v[mask], p[mask], q[mask]], axis=-1)

    return rgb


def render_camera_preview(
    rgb_frame: np.ndarray | None,
    depth_frame: np.ndarray | None,
    layout: str = "horizontal",
) -> None:
    """Render camera preview with RGB and Depth side by side.

    Args:
        rgb_frame: RGB image (H, W, 3) in BGR or RGB format
        depth_frame: Depth image (H, W) in uint16 mm or float32 m
        layout: "horizontal" or "vertical"
    """
    if layout == "horizontal":
        col1, col2 = st.columns(2)
    else:
        col1 = col2 = st.container()

    with col1:
        st.markdown("**RGB**")
        if rgb_frame is not None:
            # Convert BGR to RGB if needed
            if rgb_frame.shape[2] == 3:
                # Assume BGR from OpenCV, convert to RGB
                display_rgb = rgb_frame[:, :, ::-1]
            else:
                display_rgb = rgb_frame
            st.image(display_rgb, use_container_width=True)
        else:
            st.info("No RGB frame")

    with col2:
        st.markdown("**Depth**")
        if depth_frame is not None:
            depth_colored = colorize_depth(depth_frame)
            st.image(depth_colored, use_container_width=True)
        else:
            st.info("No Depth frame")


def render_quality_overlay(
    frame: np.ndarray,
    quality_metrics: dict[str, Any],
) -> None:
    """Render a frame with quality metrics overlay.

    Args:
        frame: RGB or colorized depth image
        quality_metrics: Dictionary with quality information
    """
    col1, col2 = st.columns([3, 1])

    with col1:
        st.image(frame, use_container_width=True)

    with col2:
        # Display quality metrics
        if "depth_valid_ratio" in quality_metrics:
            ratio = quality_metrics["depth_valid_ratio"]
            color = "#28a745" if ratio > 0.7 else "#ffc107" if ratio > 0.5 else "#dc3545"
            st.markdown(
                f'<p style="color: {color};">Depth Valid: {ratio:.0%}</p>',
                unsafe_allow_html=True,
            )

        if "blur_score" in quality_metrics:
            score = quality_metrics["blur_score"]
            color = "#28a745" if score > 0.6 else "#ffc107" if score > 0.4 else "#dc3545"
            st.markdown(
                f'<p style="color: {color};">Blur: {score:.0%}</p>',
                unsafe_allow_html=True,
            )

        if "is_keyframe" in quality_metrics:
            if quality_metrics["is_keyframe"]:
                st.markdown(
                    '<p style="color: #28a745;">★ Keyframe</p>',
                    unsafe_allow_html=True,
                )


def render_coverage_map(
    coverage_data: dict[str, float],
) -> None:
    """Render a simple coverage map visualization.

    Args:
        coverage_data: Dictionary with coverage ratios for different regions
    """
    st.markdown("**Coverage Map**")

    # Simple text-based coverage display
    regions = {
        "Top": coverage_data.get("top", 0.0),
        "Front": coverage_data.get("front", 0.0),
        "Back": coverage_data.get("back", 0.0),
        "Left": coverage_data.get("left", 0.0),
        "Right": coverage_data.get("right", 0.0),
        "Bottom": coverage_data.get("bottom", 0.0),
    }

    cols = st.columns(3)

    for i, (region, coverage) in enumerate(regions.items()):
        col_idx = i % 3
        with cols[col_idx]:
            color = "#28a745" if coverage > 0.7 else "#ffc107" if coverage > 0.4 else "#dc3545"
            st.markdown(
                f"""
                <div style="text-align: center; padding: 8px; background: {color}20; border-radius: 4px; margin: 2px;">
                    <span style="color: {color}; font-weight: bold;">{region}</span><br>
                    <span style="font-size: 18px;">{coverage:.0%}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
