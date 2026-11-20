"""USAGE: python -I tools/xyz_on_sheet.py PREFIX PHOTO|ortho OUT.json FILE.json:KEY [FILE.json:KEY ...]
Where does a 3D line (chair frame, e.g. the "<name>_xyz" of a tools/edge_tri.py result) appear on a FLAT rectified sheet in
one photo? Each point is carried along that photo's ray down to the sheet plane, so the curve can be drawn straight onto
PREFIX_<photo>.png (tools/ortho_view.py --img PHOTO --curves OUT.json): an independent check of a line triangulated from
other photos. "ortho" instead of a photo number drops the points square onto the plane and adds "<key>_depth_mm".
Output JSON {KEY: [[u, v], ...]}. Tiny compute."""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
import numpy as np
from rocker.cameras import Cameras
prefix, photo, out = sys.argv[1:4]; pj = json.load(open(prefix + "_plane.json")); o, eu, ev, n = (np.array(pj[k], float) for k in ("origin", "u", "v", "n")); res = {}
C = None if photo == "ortho" else Cameras.load().views[f"IMG_{photo}.JPG"].center
for spec in sys.argv[4:]:
    f, key = spec.rsplit(":", 1); X = np.array(json.load(open(f))[key], float)
    if C is None: P = X - ((X - o) @ n)[:, None] * n; res[key + "_depth_mm"] = ((X - o) @ n).round(2).tolist()
    else: t = ((o - C) @ n) / ((X - C) @ n); P = C + t[:, None] * (X - C)
    res[key] = np.c_[(P - o) @ eu, (P - o) @ ev].round(2).tolist()
json.dump(res, open(out, "w"))
print(out, {k: (round(min(p[1] for p in v)), round(max(p[1] for p in v))) for k, v in res.items() if not k.endswith("_depth_mm")})
