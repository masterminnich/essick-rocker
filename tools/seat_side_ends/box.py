"""USAGE: work/toolkit/rk.sh tools/seat_side_ends/box.py PHOTO SIDE Y0 Y1 [MARGIN_PX]  -- pixel box "X0 Y0 X1 Y1" (displayed photo) around the seat's side edge
(top arris to bottom arris of parts/seat_edge.json) between y Y0 and Y1, and the px per mm there. For tools/seat_scoop/overlay_edge.py."""
import sys, json, numpy as np
sys.path.insert(0, ".")
from rocker.cameras import Cameras
n, s, y0, y1 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]); m = float(sys.argv[5]) if len(sys.argv) > 5 else 60
E = json.load(open("parts/seat_edge.json"))[{"L": "left", "R": "right"}[s]]; P = np.r_[np.array(E["top_arris_side_xyz"]), np.array(E["bottom_arris_xyz"])]
ys = np.linspace(y0, y1, 12); Q = []
for k in ("top_arris_side_xyz", "bottom_arris_xyz"):
    A = np.array(E[k]); A = A[np.argsort(A[:, 1])]; Q += [[np.interp(y, A[:, 1], A[:, 0]), y, np.interp(y, A[:, 1], A[:, 2])] for y in ys]
Q = np.array(Q); u = Cameras.load().project_disp(f"IMG_{n}.JPG", Q); lo, hi = u.min(0) - m, u.max(0) + m
pxmm = np.median(np.linalg.norm(np.diff(u[:12], axis=0), axis=1) / np.linalg.norm(np.diff(Q[:12], axis=0), axis=1))
print(f"{int(max(lo[0], 0))} {int(max(lo[1], 0))} {int(hi[0])} {int(hi[1])}", round(float(pxmm), 2))
