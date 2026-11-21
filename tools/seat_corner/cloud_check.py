"""USAGE: tools/py.sh tools/seat_corner/cloud_check.py [--glb parts/model_v19_shapes.glb] [--out work/seatcorner/cloud_check.json]
Dense chair cloud (work/dense/chair_dense.npy, both halves, independent of the seat session's tape dots) minus the model's
seat top, in boxes near the front corners, right and mirrored left. The cloud carries a front/back bias of its own (seat/REPORT.md:
about -1.8 mm at y 460-540, the same on both halves), so the RIGHT MINUS LEFT difference is the clean number; the per-side numbers
are only indicative. Also: tape dots minus the model top (right half only). Light: one mesh, ~100k points, < 1 GB, seconds."""
import sys, json, argparse; from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
import numpy as np, trimesh, csv
ap = argparse.ArgumentParser(); ap.add_argument("--glb", default="parts/model_v19_shapes.glb"); ap.add_argument("--out", default="work/seatcorner/cloud_check.json")
a = ap.parse_args()
from tools.seat_corner.common import seat_top_z_fn
top_z = seat_top_z_fn(ROOT / a.glb)
C = np.load(ROOT / "work/dense/chair_dense.npy")[:, :3]
sel = (np.abs(C[:, 0]) > 60) & (np.abs(C[:, 0]) < 275) & (C[:, 1] > 300) & (C[:, 1] < 545) & (C[:, 2] > 350) & (C[:, 2] < 450)
P = C[sel]; zm = top_z(P[:, :2]); d = P[:, 2] - zm; ok = np.isfinite(d) & (np.abs(d) < 8)    # points on the top (legs, arms, front face dropped)
P, d = P[ok], d[ok]
XB = [(60, 140), (140, 180), (180, 210), (210, 240), (240, 270)]; YB = [(300, 380), (380, 440), (440, 480), (480, 510), (510, 545)]
def stat(v): return {"n": int(len(v)), "median": float(np.median(v)), "mad_sigma": float(1.4826 * np.median(np.abs(v - np.median(v))))} if len(v) >= 8 else {"n": int(len(v))}
res = {"note": __doc__.split("\n")[1], "glb": a.glb, "boxes": []}
print("box |x|, y           right: n median    left: n median    R-L   (cloud minus model top, mm)")
for x0, x1 in XB:
    for y0, y1 in YB:
        m = (np.abs(P[:, 0]) >= x0) & (np.abs(P[:, 0]) < x1) & (P[:, 1] >= y0) & (P[:, 1] < y1)
        r, l = d[m & (P[:, 0] > 0)], d[m & (P[:, 0] < 0)]; sr, sl = stat(r), stat(l)
        rl = sr.get("median", np.nan) - sl.get("median", np.nan)
        res["boxes"].append({"abs_x": [x0, x1], "y": [y0, y1], "right": sr, "left": sl, "right_minus_left": None if np.isnan(rl) else float(rl)})
        print(f"{x0:3d}-{x1:3d}, {y0:3d}-{y1:3d}   {sr['n']:5d} {sr.get('median', np.nan):6.2f}   {sl['n']:5d} {sl.get('median', np.nan):6.2f}   {rl:6.2f}")
# tape dots (right half) minus the model top
D = list(csv.DictReader(open(ROOT / "seat/dots.csv"))); X = np.array([[float(r["x_mm"]), float(r["y_mm"]), float(r["z_mm"])] for r in D]); ids = [r["id"] for r in D]
zd = top_z(X[:, :2]); dd = X[:, 2] - zd
near = (X[:, 0] > 140) & (X[:, 1] > 380) & np.isfinite(dd)
res["dots_minus_model_near_corner"] = [{"id": ids[i], "x": float(X[i, 0]), "y": float(X[i, 1]), "z": float(X[i, 2]), "minus_model": float(dd[i])} for i in np.where(near)[0]]
print("dots near the right front corner (x > 140, y > 380): id x y z  dot-model")
for r in res["dots_minus_model_near_corner"]: print(f"  {r['id']:>4} {r['x']:6.1f} {r['y']:6.1f} {r['z']:6.1f}  {r['minus_model']:+5.2f}")
Path(ROOT / a.out).parent.mkdir(parents=True, exist_ok=True); json.dump(res, open(ROOT / a.out, "w"), indent=1); print("wrote", a.out)
