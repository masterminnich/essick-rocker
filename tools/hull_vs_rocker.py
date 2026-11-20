"""USAGE: python -I tools/hull_vs_rocker.py --npz parts/hull_v1.npz [--keep 0.97]
Accuracy check of the carved hull against the one part known to ~1 mm: the left rocker's traced side profile.
Takes hull voxels inside the rocker's thickness (3-22 mm behind its outer face), and per 10 mm station along the rocker
compares the hull's top and bottom with the traced top and bottom edges. Leg stations are skipped. Tiny compute."""
import json, argparse, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--npz", required=True); ap.add_argument("--keep", type=float, default=0.97); a = ap.parse_args()
z = np.load(a.npz); F = z["F"]; lo = z["lo"]; vox = float(z["voxel"])
pj = json.load(open("work/parts/rockerL/o_plane.json")); o, u, v, n = (np.array(pj[k]) for k in ("origin", "u", "v", "n"))
rp = json.load(open("parts/rocker_profile.json")); U = np.array(rp["u"]); top = np.array(rp["left"]["top"]); bot = np.array(rp["left"]["bot"])
idx = np.argwhere(F[:, :, :int(260 / vox)] >= a.keep); X = lo + (idx + 0.5) * vox; X = X[X[:, 0] < -80]
d = X - o; uu, vv, dep = d @ u, d @ v, -(d @ n)
m = (dep > 3) & (dep < 22) & (uu > -470) & (uu < 610) & (vv < np.interp(uu, U, top) + 30) & (vv > np.interp(uu, U, bot) - 30)
uu, vv = uu[m], vv[m]; rows = []
for u0 in np.arange(-460, 600, 10):
    if 5 < u0 < 95 or 505 < u0 < 610: continue           # back-leg and front-leg stations
    s = vv[np.abs(uu - u0) < 5]
    if len(s) < 5: rows.append((u0, np.nan, np.nan)); continue
    rows.append((u0, s.max() + vox / 2 - np.interp(u0, U, top), s.min() - vox / 2 - np.interp(u0, U, bot)))
R = np.array(rows); ok = np.isfinite(R[:, 1])
print(f"stations {len(R)}, with hull {ok.sum()}  (voxel {vox} mm; + = hull sticks out beyond the traced edge)")
for nm, c in (("top edge", 1), ("bottom edge", 2)):
    r = R[ok, c]; print(f"  {nm}: median {np.median(r):+.1f} mm, 10th..90th pct {np.percentile(r, 10):+.1f} .. {np.percentile(r, 90):+.1f}, worst {r[np.abs(r).argmax()]:+.1f}")
h = (R[ok, 1] - R[ok, 2]); print(f"  hull face height minus traced: median {np.median(h):+.1f} mm")
for seg in ((-460, -200), (-200, 5), (95, 345), (345, 505)):
    q = ok & (R[:, 0] >= seg[0]) & (R[:, 0] < seg[1])
    if q.sum(): print(f"    u {seg}: top {np.median(R[q, 1]):+.1f}  bottom {np.median(R[q, 2]):+.1f}")
