"""USAGE: work/toolkit/rk.sh tools/seat_roll/pick.py OUT.json STRIP.npz [STRIP.npz ...] [--lo -3 --hi 5 --wood -4 -1.5]
Wood edge in each row of the unrolled strips that tools/seat_roll/strip.py writes. Per row: the wood colour is the median Lab
over t -4..-1.5 mm (inside the wood; --wood); the edge is the first t in [lo, hi] where the colour distance from the wood passes half
the distance to the colour 2.5 mm beyond it (sub-sample by linear interpolation). Rows with too little contrast (< 12 Lab)
are dropped. + t = the wood reaches beyond (below / in front of) the design line = the model lies INSIDE the wood there by t.
Writes, per strip: photo, side, pxmm, and per row x, t_edge, contrast. Prints a per-strip summary by |x| bin."""
import sys, json, argparse
from pathlib import Path
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("strips", nargs="+")
ap.add_argument("--lo", type=float, default=-3); ap.add_argument("--hi", type=float, default=5); ap.add_argument("--wood", type=float, nargs=2, default=[-4, -1.5])
a = ap.parse_args()
res = []
for f in a.strips:
    d = np.load(f); lab, T, X, ok = d["lab"], d["t"], d["x"], d["ok"]
    name = Path(f).stem.split("_"); photo, side = name[-2], name[-1]
    rows = []
    for i in range(len(X)):
        if not ok[i]: continue
        L = lab[i]
        wood = np.median(L[(T >= a.wood[0]) & (T <= a.wood[1])], axis=0)
        dist = np.linalg.norm(L - wood, axis=1)
        sel = np.where((T >= a.lo) & (T <= a.hi))[0]
        te = None
        for j in sel:
            k = j + 25
            if k >= len(T): break
            far = np.linalg.norm(L[k] - wood)
            if far < 12: continue
            if dist[j] >= 0.5 * far and dist[j - 1] < 0.5 * far:
                f0 = (0.5 * far - dist[j - 1]) / max(dist[j] - dist[j - 1], 1e-6)
                te = T[j - 1] + f0 * (T[j] - T[j - 1]); con = far; break
        if te is not None: rows.append(dict(x=float(X[i]), t=float(te), con=float(con)))
    pm = float(np.median(d["pxmm"][ok]))
    res.append(dict(photo=photo, side=side, pxmm=pm, rows=rows))
    ax = np.array([abs(r["x"]) for r in rows]); tt = np.array([r["t"] for r in rows])
    s = []
    for b0 in range(0, 250, 50 if np.abs(X).max() > 200 else 40):
        m = (ax >= b0) & (ax < b0 + (50 if np.abs(X).max() > 200 else 40))
        s.append(f"{b0:3d}:{np.median(tt[m]):+5.2f}({m.sum():2d})" if m.sum() >= 5 else f"{b0:3d}:   --   ")
    print(photo, side, f"{pm:.1f}px/mm", " ".join(s))
json.dump(res, open(a.out, "w"), indent=0)
