"""Cache clean orthophotos (no grid) of each front leg's outer face, 0.1 mm/px, u -50..40, v -40..80 (plane of tools/domino_ortho.py
on model v18 shapes). Writes work/fdom/raw/<leg>_<photo>.png and work/fdom/raw/planes.json. One photo decoded at a time."""
import sys, json; sys.path.insert(0, ".")
import numpy as np, cv2
from rocker.cameras import Cameras
from rocker.ortho import Plane, ortho
P = json.load(open("work/fdom/ortho/planes.json")); cams = Cameras.load(); out = {}; UR, VR, RES = (-50, 40), (-40, 80), 0.1
import os; os.makedirs("work/fdom/raw", exist_ok=True)
for leg, d in P.items():
    sgn = 1 if leg.endswith("R") else -1; c = np.array(d["origin"], float); n = np.array(d["normal"], float); n /= np.linalg.norm(n)
    v = np.array([0, 0, 1.0]); v -= n * (v @ n); v /= np.linalg.norm(v); u = np.cross(v, n) * sgn
    if u[1] < 0: u = -u
    pl = Plane(c, u, v); out[leg] = {"origin": c.tolist(), "u": pl.u.tolist(), "v": pl.v.tolist(), "n": n.tolist(), "urange": UR, "vrange": VR, "res": RES, "photos": d["photos"]}
    for nm, ang in d["photos"]:
        img = ortho(cams, nm, pl, UR, VR, RES); cv2.imwrite(f"work/fdom/raw/{leg}_{nm[4:8]}.png", img)
json.dump(out, open("work/fdom/raw/planes.json", "w"), indent=1); print("ok")
