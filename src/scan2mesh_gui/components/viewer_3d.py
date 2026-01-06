"""3D viewer components using PyVista."""

from pathlib import Path

import streamlit as st


# Note: pyvista and stpyvista are optional dependencies
try:
    import pyvista as pv
    from stpyvista import stpyvista
    PYVISTA_AVAILABLE = True
except ImportError:
    PYVISTA_AVAILABLE = False


def render_mesh_viewer(
    mesh_path: Path,
    height: int = 400,
    show_edges: bool = False,
) -> None:
    """Render an interactive 3D mesh viewer.

    Args:
        mesh_path: Path to the mesh file (GLB, OBJ, PLY, etc.)
        height: Viewer height in pixels
        show_edges: Whether to show mesh edges
    """
    if not PYVISTA_AVAILABLE:
        st.warning("PyVista is not installed. Install with: pip install pyvista stpyvista")
        return

    if not mesh_path.exists():
        st.error(f"Mesh file not found: {mesh_path}")
        return

    try:
        # Load mesh
        mesh = pv.read(str(mesh_path))

        # Create plotter
        plotter = pv.Plotter(window_size=[800, height])
        plotter.add_mesh(
            mesh,
            show_edges=show_edges,
            color="lightblue" if not mesh.n_arrays else None,
            scalars=mesh.active_scalars_name if mesh.n_arrays else None,
        )
        plotter.add_axes()
        plotter.view_isometric()

        # Render in Streamlit
        stpyvista(plotter, key=f"mesh_{mesh_path.name}")

    except Exception as e:
        st.error(f"Failed to load mesh: {e}")


def render_pointcloud_viewer(
    ply_path: Path,
    height: int = 400,
    point_size: float = 2.0,
) -> None:
    """Render an interactive point cloud viewer.

    Args:
        ply_path: Path to the PLY file
        height: Viewer height in pixels
        point_size: Size of points
    """
    if not PYVISTA_AVAILABLE:
        st.warning("PyVista is not installed. Install with: pip install pyvista stpyvista")
        return

    if not ply_path.exists():
        st.error(f"Point cloud file not found: {ply_path}")
        return

    try:
        # Load point cloud
        cloud = pv.read(str(ply_path))

        # Create plotter
        plotter = pv.Plotter(window_size=[800, height])
        plotter.add_points(
            cloud,
            point_size=point_size,
            render_points_as_spheres=True,
            scalars=cloud.active_scalars_name if cloud.n_arrays else None,
        )
        plotter.add_axes()
        plotter.view_isometric()

        # Render in Streamlit
        stpyvista(plotter, key=f"cloud_{ply_path.name}")

    except Exception as e:
        st.error(f"Failed to load point cloud: {e}")


def render_lod_comparison(
    lod_paths: list[Path],
    height: int = 300,
) -> None:
    """Render LOD meshes side by side for comparison.

    Args:
        lod_paths: List of paths to LOD mesh files (LOD0, LOD1, LOD2)
        height: Viewer height per mesh
    """
    if not PYVISTA_AVAILABLE:
        st.warning("PyVista is not installed. Install with: pip install pyvista stpyvista")
        return

    cols = st.columns(len(lod_paths))

    for i, (col, path) in enumerate(zip(cols, lod_paths)):
        with col:
            st.markdown(f"**LOD{i}**")
            if path.exists():
                render_mesh_viewer(path, height=height)

                # Show triangle count
                try:
                    mesh = pv.read(str(path))
                    st.caption(f"Triangles: {mesh.n_faces:,}")
                except Exception:
                    pass
            else:
                st.info("Not available")


def render_mesh_preview_image(
    mesh_path: Path,
    output_path: Path | None = None,
    width: int = 400,
    height: int = 400,
) -> Path | None:
    """Render a static preview image of a mesh.

    Args:
        mesh_path: Path to the mesh file
        output_path: Optional path to save the image
        width: Image width
        height: Image height

    Returns:
        Path to the saved image, or None if failed
    """
    if not PYVISTA_AVAILABLE:
        return None

    if not mesh_path.exists():
        return None

    try:
        # Load mesh
        mesh = pv.read(str(mesh_path))

        # Create off-screen plotter
        plotter = pv.Plotter(off_screen=True, window_size=[width, height])
        plotter.add_mesh(mesh, color="lightblue")
        plotter.view_isometric()
        plotter.add_axes()

        # Determine output path
        if output_path is None:
            output_path = mesh_path.with_suffix(".png")

        # Save screenshot
        plotter.screenshot(str(output_path))

        return output_path

    except Exception:
        return None
