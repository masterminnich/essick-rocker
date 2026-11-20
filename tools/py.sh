#!/bin/bash
# USAGE: tools/py.sh [-m GB] [-t MIN] script.py args...   -- run a project script through the capped runner with the full env
cd "$(dirname "$0")/.."
M=3; T=8
while [ "$1" = "-m" ] || [ "$1" = "-t" ]; do [ "$1" = "-m" ] && M=$2 || T=$2; shift 2; done
tools/safe_run.sh -m $M -t $T -- uv run -q --no-project --with numpy --with scipy --with trimesh --with shapely --with mapbox_earcut --with networkx --with pycolmap --with pillow --with opencv-python-headless --with scikit-image --with matplotlib python -I "$@"
