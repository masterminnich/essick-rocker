#!/bin/zsh
# USAGE: tools/zoom_panels.sh PREFIX OUT.jpg SCALE GRID "U0 U1 V0 V1" ["U0 U1 V0 V1" ...] [-- CURVES.json]
# env IMG="--img 1502" picks a single rectified photo instead of the median.
# Close-up gridded panels of an orthophoto side by side (red separators), for placing edge seeds by eye.
P=$1; O=$2; S=$3; G=$4; shift 4; i=0; L=(); C=(); T=$(mktemp -d /tmp/zp.XXXXXX)   # own temp folder: sessions sharing /tmp/_zp_N.jpg overwrote each other's panels
for w in "$@"; do
  if [[ "$w" == "--" ]]; then continue; fi
  if [[ "$w" == *.json ]]; then C=(--curves $w); continue; fi
done
for w in "$@"; do
  if [[ "$w" == "--" || "$w" == *.json ]]; then continue; fi
  i=$((i+1)); work/toolkit/rk.sh tools/ortho_view.py "$P" --scale $S --grid $G --window ${=w} $C ${=IMG} --out $T/$i.jpg >/dev/null; L+=($T/$i.jpg)
done
work/toolkit/rk.sh - "$O" $L <<'PY'
import sys, cv2, numpy as np
ims = [cv2.imread(f) for f in sys.argv[2:]]; H = max(i.shape[0] for i in ims)
cv2.imwrite(sys.argv[1], np.hstack([cv2.copyMakeBorder(i, 0, H - i.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=(0, 0, 255)) for i in ims]))
print(sys.argv[1], [i.shape[:2] for i in ims])
PY
rm -rf $T
