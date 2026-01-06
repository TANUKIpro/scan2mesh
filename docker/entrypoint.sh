#!/bin/bash
set -e

# Set PATH to include virtual environment
export PATH="/opt/venv/bin:$PATH"

# scan2mesh Docker entrypoint script
# This script is executed when the container starts

# Default to running scan2mesh if no command is provided
if [ $# -eq 0 ]; then
    echo "scan2mesh container started successfully."
    echo "Usage: docker run scan2mesh <command>"
    echo ""
    echo "Examples:"
    echo "  docker run scan2mesh scan2mesh --help"
    echo "  docker run scan2mesh scan2mesh init --name my_object"
    echo "  docker run scan2mesh pytest"
    echo ""
    exec /opt/venv/bin/scan2mesh --help
else
    exec "$@"
fi
