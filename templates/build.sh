#!/bin/bash
# USAGE: templates/build.sh   -- rebuild every template from parts/*.json (run from the repo root of this worktree).
# One job at a time through tools/py.sh (each step < 1 GB, a few seconds). Outputs: templates/out/*.pdf|dxf|png, figures/templates/.
set -e
cd "$(dirname "$0")/.."
tools/py.sh templates/rocker.py
mkdir -p figures/templates
tools/py.sh templates/check_overlay.py --geom templates/out/rocker_geom.json --out figures/templates/rocker_overlay.jpg
tools/py.sh templates/slats.py
tools/py.sh templates/check_slat_overlay.py --geom templates/out/slats_geom.json --out figures/templates/slat_overlay.jpg
# rocker vs the PR #6 template (numbers for the LEDGER): git show f3b1348:templates/out/rocker_geom.json > /tmp/rocker_geom_old.json && tools/py.sh templates/rocker_vs_old.py --old /tmp/rocker_geom_old.json
tools/py.sh templates/seat.py
tools/py.sh templates/check_seat_overlay.py --geom templates/out/seat_geom.json --out figures/templates/seat_overlay.jpg
tools/py.sh templates/crest.py
tools/py.sh templates/check_crest_overlay.py --geom templates/out/crest_geom.json --out figures/templates/crest_overlay.jpg
tools/py.sh templates/arms.py
tools/py.sh templates/check_arm_overlay.py --geom templates/out/arms_geom.json --out figures/templates/arms_overlay.jpg
