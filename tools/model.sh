#!/bin/bash
# USAGE: tools/model.sh --out parts/model_vN [build_model.py args] [--shapes-only]
# The whole build, one capped job after the other (never in parallel):
#   1. tools/build_model.py   the parts as traced            -> <out>_shapes.glb, <out>_params.json, <out>_edges.json
#   2. tools/joinery.py       the joints cut into them        -> <out>.glb (the chair), <out>_joinery.json
#   3. tools/audit_joints.py  the assembly check on <out>.glb -> <out>_joints.json, then tools/joints_gate.py prints PASS / FAIL
#   4. tools/joint_quality.py flush faces / shards / steps at the arm end on the back leg -> <out>_joint_quality.json (a report;
#                             it does not fail the build while only the right arm is built by rule)
# --shapes-only stops after step 1 and writes <out>.glb as before (for quick trials of one part).
cd "$(dirname "$0")/.."
out=""; shapes_only=0; args=()
while [ $# -gt 0 ]; do
  case "$1" in
    --out) out="$2"; shift 2 ;;
    --shapes-only) shapes_only=1; shift ;;
    *) args+=("$1"); shift ;;
  esac
done
[ -n "$out" ] || { echo "model.sh: --out is required"; exit 2; }
BUILD="uv run -q --no-project --with numpy --with scipy --with trimesh --with rtree --with shapely --with mapbox_earcut --with networkx --with pycolmap --with pillow --with opencv-python-headless python -I"
JOIN="uv run -q --no-project --with numpy --with scipy --with trimesh --with rtree --with manifold3d --with networkx --with pymeshfix --with shapely --with mapbox_earcut python -I"
run() {   # the lock is shared with the other worktrees: wait and retry while another job holds it
  for try in 1 2 3 4 5 6 7 8 9 10; do
    log=$(mktemp); "$@" > "$log" 2>&1; rc=$?
    if grep -q refusing "$log"; then rm -f "$log"; sleep 15; continue; fi
    cat "$log"; rm -f "$log"; return $rc
  done
  echo "model.sh: the compute lock stayed busy"; return 1
}
if [ $shapes_only = 1 ]; then run tools/safe_run.sh -m 2 -t 5 -- $BUILD tools/build_model.py --out "$out" "${args[@]}"; exit $?; fi
run tools/safe_run.sh -m 2 -t 5 -- $BUILD tools/build_model.py --out "${out}_shapes" "${args[@]}" || exit 1
mv "${out}_shapes_params.json" "${out}_params.json"; mv "${out}_shapes_edges.json" "${out}_edges.json"
mkdir -p work/logs; L="work/logs/$(basename "$out")"
run tools/safe_run.sh -m 3 -t 5 -- $JOIN tools/joinery.py "${out}_shapes.glb" "${out}.glb" > "${L}_joinery.log" || { tail -5 "${L}_joinery.log"; echo "model.sh: joinery failed"; exit 1; }
run tools/safe_run.sh -m 3 -t 6 -- $JOIN tools/audit_joints.py "${out}.glb" "${out}_joints.json" > "${L}_joints.log" || { tail -5 "${L}_joints.log"; echo "model.sh: assembly check failed to run"; exit 1; }
python3 -I tools/joints_gate.py "${out}_joints.json" "${out}_joinery.json"; rc=$?
run tools/safe_run.sh -m 3 -t 5 -- $JOIN tools/joint_quality.py "${out}.glb" "${out}_joint_quality.json" | grep -E '^ARM_'
exit $rc
