"""Entry point for running scan2mesh as a module.

Usage:
    python -m scan2mesh [command] [options]
"""

from scan2mesh.cli import app


if __name__ == "__main__":
    app()
