"""USAGE: work/toolkit/rk.sh tools/rocker_thickness/fit.py RIBDIR OUT.json [STEP 20] [HALF 10]
Step 3. Per side and station (every STEP mm of u, columns within +-HALF): per photo the median of d_out, d_in and of the
thickness T = d_in - d_out over the columns where both arrises were traced (>= 5 columns). Then over the photos:
  T_obs = T0 + k * s * cot(el)       (s = +1 camera outboard, -1 inboard; el = the camera's elevation above the top face)
The second term is what a difference in height between the inner and the outer arris (k mm, inner higher) does to an orthophoto
taken on a flat, square top face; with cameras on both sides it separates from T0. Robust (Huber, 1.5 x MAD) least squares;
se from the residuals. Also the plain median of T over photos, its spread (1.4826 x MAD) and the median positions d_out / d_in
(each moved by the photo's pose error, so +-1-3 mm per photo; their median is the face position, the T is pose-free).
Photos with fewer than 5 such stations on that side are dropped (one-off views)."""
import sys, json
import numpy as np
rib, outp = sys.argv[1], sys.argv[2]; STEP = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0; HALF = float(sys.argv[4]) if len(sys.argv) > 4 else 10.0
R = json.load(open(f"{rib}/ribbons.json")); T = json.load(open(f"{rib}/trace.json")); g = R["grid"]
us = np.arange(g["u0"], g["u1"] + 1e-9, g["du"])
def huber(A, y):
    w = np.ones(len(y))
    for _ in range(20):
        b, *_ = np.linalg.lstsq(A * w[:, None], y * w, rcond=None); r = y - A @ b; sc = 1.4826 * np.median(np.abs(r)) + 0.05; w = 1 / np.sqrt(np.maximum(1, np.abs(r) / (1.5 * sc)))
    cov = np.linalg.pinv((A * (w ** 2)[:, None]).T @ A) * sc ** 2
    return b, np.sqrt(np.diag(cov)), sc
res = {"step": STEP, "half": HALF, "model_thickness": 31.0, "sides": {}}
for S in "LR":
    per = {}
    for ph, tr in T["sides"][S].items():
        info = R["sides"][S]["photos"][ph]; el = np.array(info["el"], float); do = np.array(tr["d_out"], float); di = np.array(tr["d_in"], float); pm = np.array(info["px_per_mm_d"], float)
        rows = {}
        for st in np.arange(-480, 621, STEP):
            c = np.abs(us - st) <= HALF; b = c & np.isfinite(do) & np.isfinite(di)
            if b.sum() < 5: continue
            rows[float(st)] = dict(T=float(np.median(di[b] - do[b])), d_out=float(np.median(do[b])), d_in=float(np.median(di[b])), el=float(np.median(el[b])), s=info["cam_side"], px=float(np.median(pm[b])), n=int(b.sum()))
        if len(rows) >= 5: per[ph] = rows
    st_out = []
    for st in np.arange(-480, 621, STEP):
        rr = [(ph, r[float(st)]) for ph, r in per.items() if float(st) in r]
        if len(rr) < 4: continue
        y = np.array([r["T"] for _, r in rr]); x = np.array([r["s"] / np.tan(np.radians(max(r["el"], 5))) for _, r in rr])
        b, se, sc = huber(np.c_[np.ones(len(y)), x], y)
        med = float(np.median(y)); spr = float(1.4826 * np.median(np.abs(y - med)))
        st_out.append(dict(u=float(st), n=len(rr), n_out=int(sum(r["s"] > 0 for _, r in rr)), n_in=int(sum(r["s"] < 0 for _, r in rr)),
                           T0=round(float(b[0]), 2), T0_se=round(float(se[0]), 2), k=round(float(b[1]), 2), k_se=round(float(se[1]), 2), res_sd=round(float(sc), 2),
                           T_median=round(med, 2), T_spread=round(spr, 2), d_out=round(float(np.median([r["d_out"] for _, r in rr])), 2), d_in=round(float(np.median([r["d_in"] for _, r in rr])), 2),
                           el=[round(float(min(r["el"] for _, r in rr)), 1), round(float(max(r["el"] for _, r in rr)), 1)], px_per_mm=round(float(np.median([r["px"] for _, r in rr])), 2),
                           photos={ph: dict(T=round(r["T"], 2), d_out=round(r["d_out"], 2), d_in=round(r["d_in"], 2), el=round(r["el"], 1), s=r["s"]) for ph, r in rr}))
        q = st_out[-1]; print(S, "u %5.0f  n %2d (%2d out / %2d in)  T0 %5.2f +- %.2f  k %+5.2f  | median %5.2f spread %.2f | d_out %+5.2f d_in %5.2f  el %s  px/mm %.1f" % (st, q["n"], q["n_out"], q["n_in"], q["T0"], q["T0_se"], q["k"], q["T_median"], q["T_spread"], q["d_out"], q["d_in"], q["el"], q["px_per_mm"]))
    res["sides"][S] = st_out
json.dump(res, open(outp, "w"), indent=0)
