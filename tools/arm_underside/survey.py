"""USAGE: work/toolkit/rk.sh tools/arm_underside/survey.py [MAXAZ 60]
Which solved photos look at each arm's OUTER side face: for both arms, the camera's azimuth off the face's outward normal (in plan),
its elevation above the arm's top line, distance, pixels per mm at the arm, and whether the arm (y 80..500, top arris and 60 mm
below it) is in frame. The arm's outer top arris is parts/arms.json left/right outer_top_arris_xyz. Tiny compute."""
import sys, json; sys.path.insert(0, ".")
import numpy as np
from rocker.cameras import Cameras
MAXAZ = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
c = Cameras.load(); A = json.load(open("parts/arms.json"))
for side, sg in (("right", 1), ("left", -1)):
    O = np.array(A[side]["outer_top_arris_xyz"]); O = O[np.argsort(O[:, 1])]
    rows = []
    for nm in c.names():
        v = c[nm]; C = np.asarray(v.center, float); seen = 0; info = []
        for y in (120, 250, 380, 470):
            P = np.array([np.interp(y, O[:, 1], O[:, i]) for i in range(3)])
            dxdy = np.interp(y + 5, O[:, 1], O[:, 0]) - np.interp(y - 5, O[:, 1], O[:, 0]); t = np.array([dxdy / 10, 1, 0]); t /= np.linalg.norm(t)
            nrm = np.cross(t, [0, 0, 1]) * sg; nrm = nrm if nrm[0] * sg > 0 else -nrm
            d = C - P; az = np.degrees(np.arctan2(d @ t, d @ nrm)); el = np.degrees(np.arctan2(d[2], np.hypot(d @ t, d @ nrm)))
            ok = v.in_image(v.project(np.array([P, P - [0, 0, 60]])), 0).all()
            if ok and abs(az) < MAXAZ: seen += 1
            info.append((y, az, el, np.linalg.norm(d), v.focal_raw / np.linalg.norm(d), ok))
        if seen: rows.append((nm[4:8], seen, info))
    print(f"== {side} arm outer face: {len(rows)} photos")
    for nm, seen, info in rows:
        print(nm, seen, "  ".join(f"y{y}: az{az:+4.0f} el{el:+4.0f} {pxmm:4.1f}px/mm{'' if ok else ' OUT'}" for y, az, el, D, pxmm, ok in info))
