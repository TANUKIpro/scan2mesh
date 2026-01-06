"""Page modules for scan2mesh GUI."""

from scan2mesh_gui.pages.dashboard import render_dashboard
from scan2mesh_gui.pages.devices import render_devices
from scan2mesh_gui.pages.profiles import render_profiles
from scan2mesh_gui.pages.registry import render_registry
from scan2mesh_gui.pages.settings import render_settings


__all__ = [
    "render_dashboard",
    "render_devices",
    "render_profiles",
    "render_registry",
    "render_settings",
]
