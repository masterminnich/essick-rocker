"""USAGE: work/toolkit/rk.sh tools/seat_roll/solve_offset.py RUNDIR EDGE OUT.json [--xbins 0,50,100,150,200,250] [--ymax Y]
Where is the wood's silhouette edge against the model's edge, from the critique's per-point gaps (tools/critique/measure.py)?
For SEAT silhouette points of one edge class (e.g. bottom/front, top/back), per photo, side (L x<-15, R x>15) and 50 mm |x|
bin: the median gap g and the median outward normal m (3D, square to the ray). A gap obeys g = m . (model - wood) (the shift
test of tools/critique/shift_check.py), so over photos from different directions
    g_p = -m_p . (dy, dz) + c
is solved per bin and side: (dy, dz) = how far the wood's edge sits from the model's (+ = forward / up), c = a part of the gap
that is the SAME from every direction (an eased arris: a sharp model stands outside a rounded edge's silhouette from every
side, c > 0; a translation flips sign with the view). Ranking photos only (tools/critique/holdout.json); held-out photos are
predicted and their residuals reported. Robust: Huber weights (1 mm), jackknife over photos for the se. dx is ignored
(the edges run along x). Tiny compute."""
import sys, json, argparse
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "tools/critique"))
from common import CLASSES
ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("edge"); ap.add_argument("out")
ap.add_argument("--xbins", default="0,50,100,150,200,250"); ap.add_argument("--no-c", action="store_true")
a = ap.parse_args(); B = [int(v) for v in a.xbins.split(",")]
HO = set(json.load(open(ROOT / "tools/critique/holdout.json"))["held_out"])
rows = []
for f in sorted(Path(a.run).glob("IMG_*.npz")):
    R = dict(np.load(f)); name = f.stem + ".JPG"
    e = np.where(R["c1"] == R["c2"], np.array(CLASSES)[R["c1"]], np.char.add(np.char.add(np.array(CLASSES)[R["c1"]], "/"), np.array(CLASSES)[R["c2"]]))
    s = (R["part"] == 0) & (R["kind"] == 1) & (R["st"] == 0) & (e == a.edge); X = R["X"]
    for sd, m in (("L", X[:, 0] < -15), ("R", X[:, 0] > 15)):
        for b in B:
            k = s & m & (np.abs(X[:, 0]) >= max(b, 15)) & (np.abs(X[:, 0]) < b + 50)
            if k.sum() < 3: continue
            rows.append(dict(photo=f.stem[4:], held=name in HO, side=sd, xbin=b, n=int(k.sum()), g=float(np.median(R["gap"][k])),
                             m=[float(v) for v in np.median(R["m"][k], 0)], pxmm=float(np.median(R["pxmm"][k]))))


def fit(G, M, c=True):
    A = np.c_[-M[:, 1], -M[:, 2], np.ones(len(G))] if c else np.c_[-M[:, 1], -M[:, 2]]
    w = np.ones(len(G))
    for _ in range(20):
        p = np.linalg.lstsq(A * w[:, None], G * w, rcond=None)[0]; r = G - A @ p; w = np.sqrt(np.minimum(1, 1.0 / np.maximum(np.abs(r), 1e-9)))
    return p, r, A


res = {"edge": a.edge, "sign": "dy, dz = wood edge minus model edge (+ forward / up); c = direction-independent part of the gap (+ = model outside the wood from every side)", "bins": []}
for sd in ("L", "R", "LR"):
    for b in B:
        T = [r for r in rows if (r["side"] == sd or sd == "LR") and r["xbin"] == b]
        tr = [r for r in T if not r["held"]]; ho = [r for r in T if r["held"]]
        if len(tr) < 4: continue
        G = np.array([r["g"] for r in tr]); M = np.array([r["m"] for r in tr])
        p, r, A = fit(G, M, not a.no_c)
        jk = []
        for i in range(len(tr)):
            k = np.arange(len(tr)) != i; jk.append(fit(G[k], M[k], not a.no_c)[0])
        jk = np.array(jk); se = np.sqrt((len(tr) - 1) / len(tr) * ((jk - jk.mean(0)) ** 2).sum(0))
        Ah = lambda rr: np.r_[-rr["m"][1], -rr["m"][2], 1.0][: 3 if not a.no_c else 2]
        hres = [rr["g"] - Ah(rr) @ p for rr in ho]
        res["bins"].append(dict(side=sd, xbin=b, n_photos=len(tr), dy=round(float(p[0]), 2), dz=round(float(p[1]), 2), c=round(float(p[2]), 2) if not a.no_c else None,
                                se=[round(float(v), 2) for v in se], rms=round(float(np.sqrt(np.mean(r ** 2))), 2), median_gap=round(float(np.median(G)), 2),
                                held=[dict(photo=rr["photo"], g=round(rr["g"], 2), resid=round(float(h), 2)) for rr, h in zip(ho, hres)],
                                m_spread=[round(float(v), 2) for v in M[:, 1:].std(0)]))
        z = res["bins"][-1]
        print(f"{sd:2s} x{b:3d} n{len(tr):2d}  dy {p[0]:+5.2f}±{se[0]:.2f}  dz {p[1]:+5.2f}±{se[1]:.2f}" + (f"  c {p[2]:+5.2f}±{se[2]:.2f}" if not a.no_c else "") +
              f"  rms {z['rms']:.2f}  med g {z['median_gap']:+.2f}  held resid " + " ".join(f"{h['photo']}:{h['resid']:+.1f}" for h in z["held"]))
json.dump(dict(res, rows=rows), open(a.out, "w"), indent=0)
