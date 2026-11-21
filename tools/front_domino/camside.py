"""Camera angle around each front leg's outer face, per photo (+ = in front of the leg). USAGE: rk.sh work/fdom/camside.py"""
import sys, json; sys.path.insert(0, ".")
import numpy as np
from rocker.cameras import Cameras
c = Cameras.load(); P = json.load(open("work/fdom/raw/planes.json"))
for leg, d in P.items():
    o, u, v, n = (np.array(d[k]) for k in ("origin", "u", "v", "n"))
    for nm, ang in d["photos"]:
        C = np.asarray(c[nm].center, float) - o; print(leg, nm[4:8], f"ang {ang:5.1f}  along u {C @ u:+7.0f}  up v {C @ v:+7.0f}  out n {C @ n:+7.0f}  -> {'FRONT' if C @ u > 0 else 'BEHIND'} az {np.degrees(np.arctan2(C @ u, C @ n)):+.0f}")
