"""CLI for scan2mesh.

This module provides the command-line interface for scan2mesh.
"""

import typer

from scan2mesh.cli.commands import (
    capture,
    init,
    optimize,
    package,
    plan,
    preprocess,
    reconstruct,
    report,
)


app = typer.Typer(
    name="scan2mesh",
    help="Generate 3D assets from RealSense RGBD camera captures.",
    no_args_is_help=True,
    add_completion=False,
)

# Register commands
app.command(name="init")(init)
app.command(name="plan")(plan)
app.command(name="capture")(capture)
app.command(name="preprocess")(preprocess)
app.command(name="reconstruct")(reconstruct)
app.command(name="optimize")(optimize)
app.command(name="package")(package)
app.command(name="report")(report)


__all__ = ["app"]
