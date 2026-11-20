#!/bin/bash
# USAGE: tools/ortho_strip.sh PREFIX CURVES.json OUT.jpg SCALE "U0 U1 V0 V1" ["U0 U1 V0 V1" ...]
# Several windows of a face orthophoto with traced curves, stacked into one image for checking.
P=$1; C=$2; O=$3; S=$4; shift 4; i=0; L=()
for w in "$@"; do i=$((i+1)); work/toolkit/rk.sh tools/ortho_view.py "$P" --scale "$S" --grid 50 --window $w --curves "$C" --out "/tmp/_strip_$i.jpg" >/dev/null; L+=("/tmp/_strip_$i.jpg"); done
work/toolkit/rk.sh - "$O" "${L[@]}" <<'PY'
import sys, cv2, numpy as np
ims = [cv2.imread(f) for f in sys.argv[2:]]; W = max(i.shape[1] for i in ims)
cv2.imwrite(sys.argv[1], np.vstack([cv2.copyMakeBorder(i, 0, 6, 0, W - i.shape[1], cv2.BORDER_CONSTANT, value=(0, 0, 0)) for i in ims]))
PY
