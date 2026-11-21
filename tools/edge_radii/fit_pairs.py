"""USAGE: work/toolkit/rk.sh tools/edge_radii/fit_pairs.py work/edge_radii/pairs_v24.npz OUT.json [--band 100] [--boot 200]
Phase 6c: fit the arris radius r per member from the pose-free silhouette pairs of pairs.py.
    S = sum_g dW[g, side, band] * c_g + r * K           (K = k_a + k_b, the two arrises' ease factors)
dW = the model's width minus the wood's across each class group, free per side (L/R) and per station band (the real chair
is not symmetric and not exactly the model's size); r is one number per member (all its arrises). Huber IRLS (scale from
the MAD), ranking photos only. se of r: bootstrap over PHOTOS (a photo's pairs move together). Held-out check: the held-out
photos' pairs predicted with the fitted dW and r, and with dW refitted for r = 0; median |residual| both ways.
"""
import sys, json, argparse
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("pairs"); ap.add_argument("out")
ap.add_argument("--band", type=float, default=100.0); ap.add_argument("--boot", type=int, default=200)
a = ap.parse_args()
D = dict(np.load(a.pairs))
MEMBER = {"ARM_L": "ARM", "ARM_R": "ARM", "FLEG_L": "FLEG", "FLEG_R": "FLEG", "BLEG_L": "BLEG", "BLEG_R": "BLEG",
          "ROCKER_L": "ROCKER", "ROCKER_R": "ROCKER", "SLAT_L": "SLAT_LR", "SLAT_R": "SLAT_LR", "CREST": "CREST",
          "SLAT_C": "SLAT_C"}
CL = ["top", "bottom", "outer", "inner", "front", "back"]
mem = np.array([MEMBER.get(p, "") for p in D["part"]])
side = np.array([p[-1] if p[-2:] in ("_L", "_R") else "C" for p in D["part"]])
band = np.floor(D["station"] / a.band).astype(int)
rng = np.random.default_rng(0)


def design(ix, fix_r=None):
    cols, names = [], []
    keys = sorted(set(zip(side[ix], band[ix])))
    for (sd, b) in keys:
        sel = (side[ix] == sd) & (band[ix] == b)
        for g in range(3):
            col = np.where(sel, D["c"][ix, g], 0.0)
            if np.abs(col).sum() > 1e-6: cols.append(col); names.append((sd, int(b), g))
    X = np.array(cols).T
    if fix_r is None: X = np.c_[X, D["K"][ix]]
    return X, names


def huber(X, y, it=20):
    w = np.ones(len(y)); beta = None
    for _ in range(it):
        W = np.sqrt(w)
        beta = np.linalg.lstsq(X * W[:, None], y * W, rcond=None)[0]
        res = y - X @ beta
        s = max(1.4826 * np.median(np.abs(res - np.median(res))), 0.05)
        u = np.abs(res) / (1.345 * s)
        w = np.where(u <= 1, 1.0, 1.0 / np.maximum(u, 1e-9))
    return beta, res, s


def fit(ix):
    X, names = design(ix)
    beta, res, s = huber(X, D["S"][ix])
    return beta[-1], beta, names, res, s


out = {}
for M in ["FLEG", "BLEG", "ARM", "ROCKER", "SLAT_LR", "SLAT_C", "CREST"]:
    ok = (mem == M) & np.isfinite(D["S"]) & (np.abs(D["S"]) < 15)
    rk = np.nonzero(ok & ~D["held"])[0]; ho = np.nonzero(ok & D["held"])[0]
    if len(rk) < 30: continue
    r, beta, names, res, s = fit(rk)
    photos = np.unique(D["photo"][rk])
    bs = []
    for _ in range(a.boot):
        pick = rng.choice(photos, len(photos))
        ix = np.concatenate([rk[D["photo"][rk] == p] for p in pick])
        try: bs.append(fit(ix)[0])
        except Exception: pass
    bs = np.array(bs)
    # held-out: predict with the fitted dW (+ r) and with dW refitted at r = 0
    Xr, nr = design(rk, fix_r=0); b0, _, _ = huber(Xr, D["S"][rk])
    def pred(ix, coef, nm, rr):
        p = np.zeros(len(ix)); have = np.zeros(len(ix), bool)
        for c_, (sd, b, g) in zip(coef, nm):
            sel = (side[ix] == sd) & (band[ix] == b)
            p += np.where(sel, c_ * D["c"][ix, g], 0); have |= sel
        return p + rr * D["K"][ix], have
    hr = {}
    if len(ho):
        p1, h1 = pred(ho, beta[:-1], names, r); p0, h0 = pred(ho, b0, nr, 0.0)
        hh = h1 & h0
        hr = dict(n_pairs=int(hh.sum()), n_photos=int(len(np.unique(D["photo"][ho][hh]))),
                  med_abs_with_r=round(float(np.median(np.abs(D["S"][ho][hh] - p1[hh]))), 3),
                  med_abs_r0=round(float(np.median(np.abs(D["S"][ho][hh] - p0[hh]))), 3),
                  mean_signed_with_r=round(float(np.mean(D["S"][ho][hh] - p1[hh])), 3),
                  mean_signed_r0=round(float(np.mean(D["S"][ho][hh] - p0[hh])), 3))
    # residual binned against K (after removing the dW terms), for the chart
    Xd, _ = design(rk); partial = D["S"][rk] - Xd[:, :-1] @ beta[:-1]
    Kq = np.quantile(D["K"][rk], np.linspace(0, 1, 7))
    bins = []
    for i in range(6):
        sel = (D["K"][rk] >= Kq[i]) & (D["K"][rk] <= Kq[i + 1])
        if sel.sum() > 5: bins.append([round(float(np.median(D["K"][rk][sel])), 3), round(float(np.median(partial[sel])), 3), int(sel.sum())])
    out[M] = dict(r_mm=round(float(r), 3), r_se_boot=round(float(np.std(bs)), 3),
                  r_boot_q=[round(float(x), 3) for x in np.quantile(bs, [0.05, 0.5, 0.95])],
                  n_pairs=int(len(rk)), n_photos=int(len(photos)), resid_scale=round(float(s), 3),
                  K_range=[round(float(x), 3) for x in np.quantile(D["K"][rk], [0.05, 0.5, 0.95])],
                  n_dW_params=len(names), pxmm_median=round(float(np.median(D["pxmm"][rk])), 2),
                  held_out=hr, partial_vs_K=bins)
    print(M, json.dumps(out[M]))
json.dump(out, open(a.out, "w"), indent=1)
