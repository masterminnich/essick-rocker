#!/bin/bash
# USAGE: templates/build.sh   -- rebuild every template from parts/*.json (run from the repo root of this worktree).
# One job at a time through tools/py.sh (each step < 1 GB, a few seconds). Outputs: templates/out/*.pdf|dxf|png, figures/templates/.
set -e
cd "$(dirname "$0")/.."
tools/py.sh templates/rocker.py
mkdir -p figures/templates
tools/py.sh templates/check_overlay.py --geom templates/out/rocker_geom.json --out figures/templates/rocker_overlay.jpg
