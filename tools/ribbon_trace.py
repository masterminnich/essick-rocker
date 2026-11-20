"""USAGE: python -I tools/ribbon_trace.py PREFIX --center "u,v u,v ..." --half HMIN HMAX [--step 1.0] [--lam 0.6] [--inner 0.02]
            [--img median] [--name NAME] [--out FILE.json]
Trace the two long edges of a ribbon-like part face (rocker, leg, arm ...) in a face orthophoto.
--center: rough centreline of the face in plane mm (a few points, +-5 mm is fine); it is splined.
--half:   the edges are searched between HMIN and HMAX mm either side of the centreline, along its normal.
At each station the colour gradient along the normal is sampled; a dynamic-programming path picks, for each side, the
edge that is strong AND continuous along the part (lam = smoothness weight, inner = preference for the nearer edge).
Output JSON: {"<name>_a": [[u,v],...], "<name>_b": [...], "<name>_center": [...]}  (a = left of travel direction).
Tiny compute (one small image)."""
import json, argparse, numpy as np, cv2
from scipy.interpolate import splprep, splev
ap = argparse.ArgumentParser(); ap.add_argument("prefix"); ap.add_argument("--center", required=True); ap.add_argument("--half", nargs=2, type=float, required=True)
ap.add_argument("--step", type=float, default=1.0); ap.add_argument("--lam", type=float, default=0.6); ap.add_argument("--inner", type=float, default=0.02)
ap.add_argument("--img", default="median"); ap.add_argument("--name", default="edge"); ap.add_argument("--out", default=None)
a = ap.parse_args()
pj = json.load(open(a.prefix + "_plane.json")); res = pj["res"]; (u0, u1), (v0, v1) = pj["urange"], pj["vrange"]
im = cv2.imread(f"{a.prefix}_{a.img}.png"); lab = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32), (0, 0), 0.8)
C = np.array([[float(x) for x in p.split(",")] for p in a.center.split()])
k = min(3, len(C) - 1); tck, _ = splprep(C.T, s=len(C) * 4.0, k=k)
tt = np.linspace(0, 1, 4000); cu = np.array(splev(tt, tck)).T
arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(cu, axis=0), axis=1))]
sta = np.arange(0, arc[-1], a.step); ti = np.interp(sta, arc, tt)
P = np.array(splev(ti, tck)).T; T = np.array(splev(ti, tck, der=1)).T; T /= np.linalg.norm(T, axis=1, keepdims=True)
N = np.stack([-T[:, 1], T[:, 0]], 1)                      # left normal
hmin, hmax = a.half; dt = res / 2
offs = np.arange(-hmax - 1, hmax + 1 + 1e-9, dt)
UV = P[:, None, :] + offs[None, :, None] * N[:, None, :]
mx = ((UV[..., 0] - u0) / res).astype(np.float32); my = ((v1 - UV[..., 1]) / res).astype(np.float32)
prof = cv2.remap(lab, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)          # stations x offsets x 3
g = np.linalg.norm(np.gradient(prof, axis=1), axis=2)
g = cv2.GaussianBlur(g, (1, 5), 0)                          # light smoothing along the part
def trace(sign):
    sel = np.flatnonzero((sign * offs >= hmin) & (sign * offs <= hmax)); o = offs[sel]; G = g[:, sel]
    Gn = G / (np.percentile(G, 95) + 1e-6) - a.inner * (np.abs(o) - hmin)
    n, m = Gn.shape; cost = np.full((n, m), -np.inf); back = np.zeros((n, m), int); cost[0] = Gn[0]
    W = int(np.ceil(2.0 / dt)); idx = np.arange(m)
    for i in range(1, n):
        best = np.full(m, -np.inf); arg = np.zeros(m, int)
        for d in range(-W, W + 1):
            j = idx + d; ok = (j >= 0) & (j < m); val = np.full(m, -np.inf); val[ok] = cost[i - 1, j[ok]] - a.lam * abs(d) * dt
            upd = val > best; best[upd] = val[upd]; arg[upd] = j[upd]
        cost[i] = best + Gn[i]; back[i] = arg
    path = np.zeros(n, int); path[-1] = int(np.argmax(cost[-1]))
    for i in range(n - 1, 0, -1): path[i - 1] = back[i, path[i]]
    # sub-sample refinement (parabola through the gradient peak)
    off = o[path].astype(float); st = np.zeros(n)
    for i, p_ in enumerate(path):
        st[i] = G[i, p_]
        if 0 < p_ < m - 1:
            y0, y1, y2 = G[i, p_ - 1], G[i, p_], G[i, p_ + 1]; den = y0 - 2 * y1 + y2
            if den < 0: off[i] += np.clip(0.5 * (y0 - y2) / den, -0.5, 0.5) * dt
    return P + off[:, None] * N, off, st
ea, oa, sa = trace(+1); eb, ob, sb = trace(-1)
out = {f"{a.name}_a": ea.tolist(), f"{a.name}_b": eb.tolist(), f"{a.name}_center": P.tolist(),
       f"{a.name}_strength_a": sa.tolist(), f"{a.name}_strength_b": sb.tolist(), "arc": sta.tolist()}
fn = a.out or f"{a.prefix}_{a.name}.json"; json.dump(out, open(fn, "w"))
w = oa - ob
print(fn, "stations", len(P), "| width between edges mm: median", np.median(w).round(2), "min", w.min().round(2), "max", w.max().round(2))
