"""USAGE: work/toolkit/rk.sh tools/slat_width/fit.py WIDTHS.npz OUT.json [--band 50] [--rho 0]
Width, thickness and turn of each slat from the silhouette widths of tools/slat_width/measure.py.

A w x t rectangle turned by th about its own length (th + = its OUTER edge forward; SLAT_C: its right edge forward) seen
across direction alpha (in the section plane, measure.py) has the silhouette width
    W(alpha) = (w - 2 rho) |cos(alpha - th)| + (t - 2 rho) |sin(alpha - th)| + 2 rho
(rho = radius of eased arrises; 0 = sharp). Both edges of W are read in the same photo, so W does not depend on the photo's
pose. Per slat and band of z (stations of measure.py pooled), robust least squares (soft L1, 0.5 mm) over the RANKING photos
(one row per photo x station), rows off by more than 3.5 x 1.4826 MAD dropped and refitted; se by a bootstrap over photos
(300 draws). The 15 held-out photos (tools/critique/holdout.json) are predicted from that fit: their median residual is the
check. Also reported: the frontal width (|alpha| < 15 deg rows only: W ~ w cos th + t |sin th|, nearly model-free) and the
width the CURRENT model would show to the same rows (w_model, t = 10, th = 0) -> residual 'model' for comparison."""
import sys, json, argparse
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
ap = argparse.ArgumentParser(); ap.add_argument("npz"); ap.add_argument("out")
ap.add_argument("--band", type=float, default=50.0); ap.add_argument("--rho", type=float, default=0.0)
ap.add_argument("--zlo", type=float, default=350); ap.add_argument("--zhi", type=float, default=1025)
ap.add_argument("--fix-t", type=float, default=None, help="hold t at this value (mm)")
a = ap.parse_args()
D = dict(np.load(a.npz))
ok = (D["st_lo"] == 0) & (D["st_hi"] == 0)
W = D["s_hi"] - D["s_lo"]; AL = np.radians(D["alpha"])


def model(p, al, rho):
    w, t, th = p[0], p[1], p[2]
    return (w - 2 * rho) * np.abs(np.cos(al - th)) + (t - 2 * rho) * np.abs(np.sin(al - th)) + 2 * rho


def fit(Wv, al, p0):
    if a.fix_t is not None:
        f = lambda q: model([q[0], a.fix_t, q[1]], al, a.rho) - Wv
        r = least_squares(f, [p0[0], p0[2]], loss="soft_l1", f_scale=0.5); return np.array([r.x[0], a.fix_t, r.x[1]])
    r = least_squares(lambda q: model(q, al, a.rho) - Wv, p0, loss="soft_l1", f_scale=0.5,
                      bounds=([10, 3, -0.6], [130, 25, 0.6]))
    return r.x


rng = np.random.default_rng(1)
out = dict(note=__doc__.split("\n\n")[0], band_mm=a.band, rho_mm=a.rho, fix_t=a.fix_t, fits=[])
for slat in ("SLAT_L", "SLAT_C", "SLAT_R"):
    for z0 in np.arange(a.zlo, a.zhi, a.band):
        s = ok & (D["slat"] == slat) & (D["z"] >= z0) & (D["z"] < z0 + a.band)
        tr = s & ~D["held"]; he = s & D["held"]
        if tr.sum() < 8: continue
        wm = float(np.median(D["w_model"][s]))
        idx = np.nonzero(tr)[0]
        p = fit(W[idx], AL[idx], [wm, 10.0, 0.0])
        r = W[idx] - model(p, AL[idx], a.rho); mad = 1.4826 * np.median(np.abs(r - np.median(r)))
        keep = idx[np.abs(r) <= max(3.5 * mad, 1.0)]
        p = fit(W[keep], AL[keep], p)
        ph = np.unique(D["photo"][keep]); bs = []
        for _ in range(300):
            pk = rng.choice(ph, len(ph)); ii = np.concatenate([keep[D["photo"][keep] == k] for k in pk])
            if len(np.unique(np.round(D["alpha"][ii] / 10))) < 3: continue
            bs.append(fit(W[ii], AL[ii], p))
        se = np.std(bs, 0)
        rk = W[keep] - model(p, AL[keep], a.rho)
        rm = W[keep] - model([wm, 10.0, 0.0], AL[keep], 0.0)
        hi_ = np.nonzero(he)[0]
        rh = W[hi_] - model(p, AL[hi_], a.rho) if len(hi_) else np.array([])
        rhm = W[hi_] - model([wm, 10.0, 0.0], AL[hi_], 0.0) if len(hi_) else np.array([])
        fr = keep[np.abs(D["alpha"][keep]) < 15]
        o = dict(slat=slat, z=float(z0 + a.band / 2), rows=int(len(keep)), dropped=int(len(idx) - len(keep)), photos=int(len(ph)),
                 w=float(p[0]), t=float(p[1]), th_deg=float(np.degrees(p[2])), se_w=float(se[0]), se_t=float(se[1]), se_th_deg=float(np.degrees(se[2])),
                 w_model=wm, resid_rms=float(np.sqrt(np.mean(rk ** 2))), resid_mad=float(1.4826 * np.median(np.abs(rk - np.median(rk)))),
                 model_resid_median=float(np.median(rm)), model_resid_rms=float(np.sqrt(np.mean(rm ** 2))),
                 held_rows=int(len(hi_)), held_photos=int(len(np.unique(D["photo"][hi_]))) if len(hi_) else 0,
                 held_resid_median=float(np.median(rh)) if len(rh) else None, held_resid_mad_abs=float(np.median(np.abs(rh))) if len(rh) else None,
                 held_model_resid_median=float(np.median(rhm)) if len(rhm) else None, held_model_mad_abs=float(np.median(np.abs(rhm))) if len(rhm) else None,
                 frontal_rows=int(len(fr)), frontal_photos=int(len(np.unique(D["photo"][fr]))),
                 frontal_W_median=float(np.median(W[fr])) if len(fr) else None,
                 frontal_W_spread=float(1.4826 * np.median(np.abs(W[fr] - np.median(W[fr])))) if len(fr) > 1 else None,
                 alpha_range=[float(D["alpha"][keep].min()), float(D["alpha"][keep].max())],
                 pxmm_median=float(np.median(D["pxmm"][keep])), pxmm_max=float(D["pxmm"][keep].max()))
        out["fits"].append(o)
        print(f"{slat} z{o['z']:6.1f} rows {o['rows']:3d}(-{o['dropped']}) ph {o['photos']:2d} a[{o['alpha_range'][0]:+4.0f},{o['alpha_range'][1]:+4.0f}] "
              f"w {p[0]:5.1f}({se[0]:.2f}) [model {wm:5.1f}] t {p[1]:4.1f}({se[1]:.2f}) th {np.degrees(p[2]):+5.1f}({np.degrees(se[2]):.1f}) "
              f"res {o['resid_mad']:.2f} model-res {o['model_resid_median']:+.2f} | held n{len(hi_)} res {o['held_resid_median'] if len(rh) else float('nan'):+.2f} "
              f"model {o['held_model_resid_median'] if len(rhm) else float('nan'):+.2f} | frontal {o['frontal_W_median'] if len(fr) else float('nan'):5.1f} n{len(fr)} px {o['pxmm_median']:.1f}")
json.dump(out, open(a.out, "w"), indent=1)
