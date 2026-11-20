#!/bin/bash
# USAGE: tools/model.sh [build_model.py args]   -- run the model builder through the capped runner
cd "$(dirname "$0")/.."
tools/safe_run.sh -m 2 -t 5 -- uv run -q --no-project --with numpy --with scipy --with trimesh --with shapely --with mapbox_earcut --with networkx --with pycolmap --with pillow --with opencv-python-headless python -I tools/build_model.py "$@"
