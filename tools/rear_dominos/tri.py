"""USAGE: work/toolkit/rk.sh tools/rear_dominos/tri.py [PLANES.json work/backdom/ortho/planes.json]
Step 3 of 3. Triangulates the tips of the Domino ends on the back legs' rear faces from their readings on the rear_ortho planes
(tools/rear_dominos/measure.py, checked by eye on the tiles): each reading is a ray from its photo's camera through the plane point;
the tip is the point closest to all its rays. Prints each tip in the chair frame, how far it sits off the model's rear face and how far
each ray misses it. The readings are the table R below (plane mm). Numbers quoted in parts/joints.json back_leg_rear and LEDGER 19:25."""
import sys, json; sys.path.insert(0, ".")
import numpy as np
from rocker.cameras import Cameras
c = Cameras.load(); PL = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "work/backdom/ortho/planes.json"))
R = {  # plane key -> feature -> {photo: (u, v)}  readings from tools/rear_dominos/measure.py (steepest tone change), checked by eye on the fine tiles
 "BLEG_L_seat": {"leg-side tip": {"1502": (7.9, -1.35), "1578": (7.6, -1.35), "1503": (6.5, -2.05), "1501": (7.5, -1.1)}},
 "BLEG_R_seat": {"leg-side tip": {"1501": (-7.4, -2.05), "1502": (-7.4, -1.25), "1499": (-7.0, -1.5)}},
 "BLEG_L_arm": {"outboard tip": {"1501": (-11.3, -12.8), "1502": (-10.9, -12.55), "1503": (-11.7, -13.25), "1499": (-11.0, -14.05), "1513": (-11.6, -14.55), "1500": (-12.0, -14.35)},
                "inboard tip": {"1502": (12.6, -12.55), "1503": (11.7, -13.25), "1499": (11.5, -14.05), "1513": (13.0, -14.55), "1500": (10.4, -14.35)}},
 "BLEG_R_arm": {"inboard tip": {"1501": (-11.0, -13.3), "1502": (-10.6, -12.7), "1503": (-11.4, -13.4), "1499": (-10.6, -14.25), "1491": (-9.9, -14.85)},
                "outboard tip": {"1501": (11.7, -13.3), "1502": (14.3, -12.7), "1503": (11.0, -13.4), "1499": (11.8, -14.25), "1491": (12.5, -14.85)}}}
out = {}
for key, feats in R.items():
    P = PL[key]; o, U, V, n = (np.array(P[k], float) for k in ("origin", "u", "v", "normal"))
    for f, obs in feats.items():
        A = np.zeros((3, 3)); b = np.zeros(3); rays = []
        for ph, (u, v) in obs.items():
            C = np.asarray(c.views[f"IMG_{ph}.JPG"].center, float); X = o + u * U + v * V; d = (X - C) / np.linalg.norm(X - C); M = np.eye(3) - np.outer(d, d); A += M; b += M @ C; rays.append((ph, C, d))
        X = np.linalg.solve(A, b); res = {ph: round(float(np.linalg.norm((np.eye(3) - np.outer(d, d)) @ (X - C))), 2) for ph, C, d in rays}
        uvp = [float((X - o) @ U), float((X - o) @ V), float((X - o) @ n)]
        out[f"{key}:{f}"] = X; print(f"{key:12s} {f:13s} xyz {X.round(1).tolist()}  on plane u {uvp[0]:+.1f} v {uvp[1]:+.1f}, {uvp[2]:+.1f} mm off the model's rear face (+ = behind it)  ray misses mm {res}")
for leg in ("L", "R"):
    a, b = out[f"BLEG_{leg}_arm:outboard tip"], out[f"BLEG_{leg}_arm:inboard tip"]; print(f"arm Domino {leg}: centre {((a + b) / 2).round(1).tolist()}  tip to tip {np.linalg.norm(a - b):.1f} mm")
