#!/bin/bash
# USAGE: tools/resid.sh MODEL.glb OUT.json   -- numeric model-vs-photo check on the standard 14-photo set, capped
cd "$(dirname "$0")/.."
tools/safe_run.sh -m 3 -t 6 -- uv run -q --no-project --with numpy --with trimesh --with pycolmap --with pillow --with opencv-python-headless --with scipy python -I tools/residual.py --glb "$1" --out "$2" --images 1471,1507,1502,1513,1496,1484,1470,1473,1505,1509,1500,1522,1527,1539
