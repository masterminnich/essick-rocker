"""USAGE: python -I tools/symmetry.py --cloud work/dense/chair_dense.npy [--apply]
Find the chair's mirror plane from its point cloud: the plane (x offset, yaw about Z, roll about Y) for which the cloud
mirrored across it lies closest to itself (trimmed mean nearest-neighbour distance). With --apply, rewrites
solve/metric_frame.json so the mirror plane is X = 0 (Z stays normal to the table) and re-expresses the cloud.
Tiny compute (14k points, KD-tree)."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
import numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import minimize
ap = argparse.ArgumentParser(); ap.add_argument("--cloud", required=True); ap.add_argument("--apply", action="store_true")
a = ap.parse_args()
C = np.load(a.cloud); P = C[(C[:, 2] > 8) & (C[:, 6] >= 3)][:, :3]
tree = cKDTree(P)
def mirror(p, Q):
    x0, yaw, roll = p
    n = np.array([np.cos(yaw) * np.cos(roll), np.sin(yaw) * np.cos(roll), np.sin(roll)])
    d = (Q - [x0, 0, 0]) @ n
    return Q - 2 * d[:, None] * n, n
def cost(p):
    M, _ = mirror(p, P); d, _ = tree.query(M); d = np.sort(d)
    return d[:int(0.8 * len(d))].mean()
best = None
for x0 in (-20, 0, 20):
    r = minimize(cost, [x0, 0, 0], method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-5, "maxiter": 600})
    if best is None or r.fun < best.fun: best = r
x0, yaw, roll = best.x
print(f"mirror plane: x0 = {x0:.2f} mm, yaw = {np.degrees(yaw):.3f} deg, roll = {np.degrees(roll):.3f} deg; trimmed mean NN = {best.fun:.2f} mm (before: {cost([0, 0, 0]):.2f})")
for dp, nm in (([1, 0, 0], "x0 +1 mm"), ([0, np.radians(0.2), 0], "yaw +0.2 deg"), ([0, 0, np.radians(0.2)], "roll +0.2 deg")):
    print("  sensitivity", nm, "-> cost", round(cost(best.x + dp), 3))
if a.apply:
    f = ROOT / "solve/metric_frame.json"; j = json.loads(f.read_text()); R = np.array(j["R"]); t = np.array(j["t"])
    # new frame: rotate about Z by yaw so the plane normal's horizontal part is +X; shift so plane passes x = 0.
    # roll (tilt of the mirror plane from vertical) is reported but NOT applied: Z stays the table normal.
    c, s_ = np.cos(-yaw), np.sin(-yaw); Rz = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])
    shift = np.array([x0, 0, 0])
    R2 = Rz @ R; t2 = Rz @ (t - shift)
    j.update(R=R2.tolist(), t=t2.tolist(), provisional_axes=False, symmetry={"x0_removed_mm": x0, "yaw_removed_deg": float(np.degrees(yaw)),
             "mirror_plane_roll_deg_not_applied": float(np.degrees(roll)), "trimmed_nn_mm": float(best.fun)})
    f.write_text(json.dumps(j, indent=1))
    C[:, :3] = (C[:, :3] - shift) @ Rz.T; np.save(a.cloud, C); print("applied; cloud re-expressed")
