"""USAGE: python -I tools/tube_tri.py PREFIX SEEDS.json OUTDIR [--only NAME]
Measure a ROLLED edge (a bullnose, no arris) from its outline in several rectified photos.
Why not tools/edge_tri.py: that tool assumes every photo outlines the same line on the part. On a rolled edge each camera sees a
different line (the horizon moves round the roll with the viewing angle), and the outline is curved in plan, so a camera
standing to one side shifts it ALONG the edge as well. Here the edge is modelled as a tube: a circle of radius r(x) swept along
a spine (x, yc(x), zc(x)). A camera's outline is where its rays touch the tube, computed exactly per camera, so photos at
different elevations fix the spine and the radius together. The plan outline of the part is the spine moved out by r.
SEEDS.json: list of {"name", "seed" ("u,v u,v ..." read by eye on seed_photo, sheet coordinates), "seed_photo", "x" [x0, x1]
(spine range, chair x), "photos" {"1545": [x0, x1], ...} (where each photo sees the edge), optional "band" (7), "r0" (12),
"node" (20: spacing of the spline nodes, mm), "smooth" [ly, lz, lr], "r_fixed" (give the radius instead of solving it: a number or [[|x|, r], ...]), "z_surface" {"weight", "offset"} or {"hard": true, "offset"} (tie the top of the roll, spine z + r, to the measured seat surface
seat/surface.json, softly or exactly: the photos fix depth poorly when their viewing angles are close together), a photo's range may be several [[x0, x1], [x2, x3]], "z_guess" (height of the outline in the seed photo;
default: the measured seat surface seat/surface.json minus 3)}.
Photos on OTHER sheets can join the same solve: "sheets" {"1558": "work/parts/seatF/ff", ...} (face_ortho prefix per photo, default
PREFIX), so cameras above (plan sheet) and cameras in front (a vertical sheet) fix one tube together. For a seed read on a
vertical sheet give "y_guess" (number or [[|x|, y], ...]: how far forward the outline is) instead of z_guess. "outward" [x, y, z]
says which side of the tube the outline is on (default forward and up: a top front edge; a bottom front edge is [0, 0.7, -0.7]).
"init": path of an earlier output to start from (its spine and radius), "init_top_z" [[x, z], ...]: height of the top of the roll
read by eye on a level front photo, replaces the starting spine height (top z minus radius), "r_bounds" [lo, hi] for a solved radius.
Each photo is traced by itself along the normal of the predicted outline (gradient + smooth path, as edge_tri), three rounds
with a shrinking band. Writes OUTDIR/<name>.json: spine, radius, plan outline, per-photo traces and fits, residuals.
Tiny compute: a few sheet PNGs, one at a time, and a least-squares fit with under 100 unknowns."""
import sys, json, argparse, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from scipy.interpolate import CubicSpline
from scipy.optimize import least_squares
from rocker.cameras import Cameras
ap = argparse.ArgumentParser(); ap.add_argument("prefix"); ap.add_argument("seeds"); ap.add_argument("outdir"); ap.add_argument("--only", default=None); ap.add_argument("--lam", type=float, default=1.5)
a = ap.parse_args(); os.makedirs(a.outdir, exist_ok=True)
cams = Cameras.load(); _SH = {}
OUTW = np.array([0.0, 0.85, 0.53])                       # default: the outline is on the forward-and-up side of the tube (a top front edge)


class Sheet:                                             # one face_ortho sheet: plane, axes, pixel grid
    def __init__(s, prefix):
        pj = json.load(open(prefix + "_plane.json")); s.prefix = prefix; s.res = pj["res"]; s.u0 = pj["urange"][0]; s.v1 = pj["vrange"][1]; s.O, s.U, s.V, s.N = (np.array(pj[k], float) for k in ("origin", "u", "v", "n"))


def sheet(prefix):
    prefix = str(prefix if os.path.exists(str(prefix) + "_plane.json") else ROOT / prefix)
    if prefix not in _SH: _SH[prefix] = Sheet(prefix)
    return _SH[prefix]


SS = json.load(open(ROOT / "seat/surface.json")); _c = np.array(SS["tps"]["centres"]); _w = np.array(SS["tps"]["w"]); _a = SS["tps"]["a"]; (mx0, mx1), (my0, my1) = SS["measured_region"]["x"], SS["measured_region"]["y"]


def tps(x, y):
    x = np.clip(np.asarray(x, float), mx0, mx1); y = np.clip(np.asarray(y, float), my0, my1); r2 = (x[:, None] - _c[None, :, 0]) ** 2 + (y[:, None] - _c[None, :, 1]) ** 2
    return (_w[None, :] * 0.5 * r2 * np.log(np.maximum(r2, 1e-12))).sum(1) + _a[0] + _a[1] * x + _a[2] * y


def proj(C, X, S):                                       # 3D points -> sheet S (u, v) as camera C sees them
    t = ((S.O - C) @ S.N) / ((X - C) @ S.N); H = C + t[:, None] * (X - C); return np.c_[(H - S.O) @ S.U, (H - S.O) @ S.V]


def contour(C, c, r, outw=OUTW):                         # where rays from C touch the tube (spine points c, radii r): 3D points
    t = np.gradient(c, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True); d = c - C; dp = d - np.sum(d * t, 1, keepdims=True) * t; D = np.linalg.norm(dp, axis=1, keepdims=True); e1 = dp / D
    e2 = np.cross(t, e1); e2 *= np.sign(e2 @ outw)[:, None]; k = r[:, None] / D
    return c + r[:, None] * (-k * e1 + np.sqrt(1 - k ** 2) * e2)


def snap(lab, P, N, band, S):                            # best smooth path of strong gradient within +-band of P along N; returns offsets
    res, u0, v1 = S.res, S.u0, S.v1; dt = res / 2; offs = np.arange(-band, band + 1e-9, dt); UV = P[:, None, :] + offs[None, :, None] * N[:, None, :]
    prof = cv2.remap(lab, ((UV[..., 0] - u0) / res).astype(np.float32), ((v1 - UV[..., 1]) / res).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    G = cv2.GaussianBlur(np.linalg.norm(np.gradient(prof, axis=1), axis=2), (1, 7), 0); Gn = G / (np.percentile(G, 95) + 1e-6)
    n, m = Gn.shape; cost = np.full((n, m), -np.inf); back = np.zeros((n, m), int); cost[0] = Gn[0]; idx = np.arange(m)
    for i in range(1, n):
        best = np.full(m, -np.inf); arg = np.zeros(m, int)
        for dd in (-1, 0, 1):
            j = idx + dd; ok = (j >= 0) & (j < m); val = np.full(m, -np.inf); val[ok] = cost[i - 1, j[ok]] - a.lam * abs(dd) * dt
            upd = val > best; best[upd] = val[upd]; arg[upd] = j[upd]
        cost[i] = best + Gn[i]; back[i] = arg
    path = np.zeros(n, int); path[-1] = int(np.argmax(cost[-1]))
    for i in range(n - 1, 0, -1): path[i - 1] = back[i, path[i]]
    return offs[path]


for L in json.load(open(a.seeds)):
    if a.only and L["name"] != a.only: continue
    name = L["name"]; xa, xb = L["x"]; xs = np.arange(min(xa, xb), max(xa, xb) + 1e-9, 2.0); node = float(L.get("node", 20)); xn = np.linspace(xs[0], xs[-1], int(round((xs[-1] - xs[0]) / node)) + 1)
    ly, lz, lr = L.get("smooth", [0.3, 0.6, 3.0]); r0 = float(L.get("r0", 12)); band = float(L.get("band", 7)); nn = len(xn)
    # first guess: the seed photo's outline put at the height of the measured seat surface, the spine r0 behind and below it
    sheets = {ph: sheet(L.get("sheets", {}).get(ph, a.prefix)) for ph in list(L["photos"]) + [L["seed_photo"]]}; S0 = sheets[L["seed_photo"]]
    outw = np.array(L.get("outward", OUTW), float); outw /= np.linalg.norm(outw)
    Sd = np.array([[float(x) for x in p.split(",")] for p in L["seed"].split()]); Cs = cams.views[f"IMG_{L['seed_photo']}.JPG"].center; Xs = S0.O + Sd[:, :1] * S0.U + Sd[:, 1:2] * S0.V; zg = Xs[:, 2].copy(); Xg = Xs.copy()
    for _ in range(4):
        if "y_guess" in L:                               # seed read on a vertical sheet: slide it along the seed camera's ray to the guessed depth
            yg = np.atleast_2d(np.array(L["y_guess"] if isinstance(L["y_guess"], list) else [[0, L["y_guess"]], [1e4, L["y_guess"]]], float)); Xg = Cs + ((np.interp(np.abs(Xg[:, 0]), yg[:, 0], yg[:, 1]) - Cs[1]) / (Xs[:, 1] - Cs[1]))[:, None] * (Xs - Cs)
        else: Xg = Cs + ((zg - Cs[2]) / (Xs[:, 2] - Cs[2]))[:, None] * (Xs - Cs); zg = np.full(len(Sd), float(L["z_guess"])) if "z_guess" in L else tps(Xg[:, 0], Xg[:, 1]) - 3.0
    o = np.argsort(Xg[:, 0]); p0 = np.r_[np.interp(xn, Xg[o, 0], Xg[o, 1]) - r0 * outw[1], np.interp(xn, Xg[o, 0], Xg[o, 2]) - r0 * outw[2], np.full(nn, r0)]
    if "init" in L:                                      # start from an earlier solve
        I = json.load(open(ROOT / L["init"])); ix = np.array(I["x"]); p0 = np.r_[np.interp(xn, ix, I["spine_y"]), np.interp(xn, ix, I["spine_z"]), np.interp(xn, ix, I["radius"])]
    rfix = L.get("r_fixed")                               # a radius the photos cannot tell apart is given, not solved: a number or [[|x|, r], ...]
    if rfix is not None:
        rf = np.atleast_2d(np.array(rfix if isinstance(rfix, list) else [[0, rfix], [1e4, rfix]], float)); rfx = np.interp(np.abs(xs), rf[:, 0], rf[:, 1]); p0[2 * nn:] = np.interp(np.abs(xn), rf[:, 0], rf[:, 1])
    if "init_top_z" in L: tz = np.array(sorted(L["init_top_z"]), float); p0[nn:2 * nn] = np.interp(xn, tz[:, 0], tz[:, 1]) - p0[2 * nn:]
    rlo, rhi = L.get("r_bounds", [-np.inf, np.inf]); lo = np.r_[np.full(2 * nn, -np.inf), np.full(nn, rlo)]; hi = np.r_[np.full(2 * nn, np.inf), np.full(nn, rhi)]; p0[2 * nn:] = np.clip(p0[2 * nn:], rlo + 0.01 if np.isfinite(rlo) else -np.inf, rhi - 0.01 if np.isfinite(rhi) else np.inf)
    zs = L.get("z_surface")                               # tie the top of the roll to the measured seat surface: {"weight": W, "offset": mm}
    hard = bool(zs and zs.get("hard")) and rfix is not None      # hard: spine z is not solved at all, it is the surface height minus the radius

    def spine(p):
        y = CubicSpline(xn, p[:nn])(xs); r = rfx if rfix is not None else CubicSpline(xn, p[2 * nn:])(xs)
        return np.c_[xs, y, tps(xs, y) + zs.get("offset", 0.0) - r if hard else CubicSpline(xn, p[nn:2 * nn])(xs)], r
    inrng = lambda rg: np.any([(xs >= min(g) - 1e-9) & (xs <= max(g) + 1e-9) for g in (rg if isinstance(rg[0], list) else [rg])], axis=0)
    views = {ph: (cams.views[f"IMG_{ph}.JPG"].center, inrng(rg)) for ph, rg in L["photos"].items()}
    labs = {ph: cv2.GaussianBlur(cv2.cvtColor(cv2.imread(f"{sheets[ph].prefix}_{ph}.png"), cv2.COLOR_BGR2LAB).astype(np.float32), (0, 0), 0.8) for ph in views}
    p = p0; obs = {}
    for rnd, bd in enumerate((band, band / 2, max(band / 3, 2.0))):
        c, r = spine(p)
        for ph, (C, msk) in views.items():
            Pp = proj(C, contour(C, c, r, outw), sheets[ph]); T = np.gradient(Pp, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True); Nn = np.c_[-T[:, 1], T[:, 0]]; off = np.zeros(len(xs)); off[msk] = snap(labs[ph], Pp[msk], Nn[msk], bd, sheets[ph])
            obs[ph] = (Pp + off[:, None] * Nn, Nn)

        def resid(q, parts=False):
            c, r = spine(q); out = {}
            for ph, (C, msk) in views.items():
                Q, Nn = obs[ph]; out[ph] = np.sum((proj(C, contour(C, c, r, outw), sheets[ph]) - Q) * Nn, 1)[msk]
            if parts: return out
            d2 = lambda v: np.diff(v, 2)
            rn = q[2 * nn:]; pin = zs["weight"] * (q[nn:2 * nn] + rn - tps(xn, q[:nn]) - zs.get("offset", 0.0)) if (zs and not hard) else np.zeros(0)
            return np.r_[np.concatenate(list(out.values())), ly * d2(q[:nn]) * 3, lz * d2(q[nn:2 * nn]) * 3, lr * d2(rn) * 3, (rn - r0) / 40.0, pin]
        sol = least_squares(resid, p, loss="soft_l1", f_scale=1.0, x_scale=1.0, max_nfev=60, bounds=(lo, hi)); p = sol.x
        pr = resid(p, True); allr = np.concatenate(list(pr.values()))
        print(f"{name} round {rnd + 1} (band {bd:.1f}): rms {np.sqrt(np.mean(allr ** 2)):.2f} mm, median |r| {np.median(np.abs(allr)):.2f} | " + ", ".join(f"{ph} {np.sqrt(np.mean(v ** 2)):.2f}" for ph, v in pr.items()))
    c, r = spine(p); tpl = np.gradient(c[:, :2], axis=0); tpl /= np.linalg.norm(tpl, axis=1, keepdims=True); nout = np.c_[-tpl[:, 1], tpl[:, 0]]; nout *= np.sign(nout[:, 1])[:, None]; plan = c[:, :2] + r[:, None] * nout
    # viewing angle of each photo round the roll (0 = straight down on the edge, + = from behind/inside), for the record
    ang = {}
    for ph, (C, msk) in views.items():
        d = C - c; hz = np.sum(d[:, :2] * nout, 1); ang[ph] = [round(float(np.degrees(np.arctan2(-hz, d[:, 2]))[msk][k]), 1) for k in (0, int(msk.sum()) // 2, -1)]
    out = {"name": name, "frame": "chair frame, mm", "x": xs.tolist(), "spine_y": c[:, 1].tolist(), "spine_z": c[:, 2].tolist(), "radius": r.tolist(), "plan_outline_xy": plan.tolist(), "top_of_roll_z": (c[:, 2] + r).tolist(),
           "residual_rms_mm": float(np.sqrt(np.mean(allr ** 2))), "per_photo_rms_mm": {ph: float(np.sqrt(np.mean(v ** 2))) for ph, v in pr.items()}, "per_photo_median_mm": {ph: float(np.median(v)) for ph, v in pr.items()},
           "photo_range_x": L["photos"], "radius_given": rfix, "outward": outw.tolist(), "bottom_of_tube_z": (c[:, 2] - r).tolist(), "z_surface": zs, "top_of_roll_minus_seat_surface_mm": (c[:, 2] + r - tps(c[:, 0], c[:, 1])).tolist(), "view_angle_round_roll_deg_start_mid_end": ang, "nodes_x": xn.tolist(),
           "per_photo": {ph: {"x": xs[msk].tolist(), "traced_uv": obs[ph][0][msk].tolist(), "fitted_uv": proj(C, contour(C, c, r, outw), sheets[ph])[msk].tolist(), "sheet": os.path.relpath(sheets[ph].prefix, ROOT), "residual_mm": pr[ph].tolist()} for ph, (C, msk) in views.items()}}
    json.dump(out, open(os.path.join(a.outdir, name + ".json"), "w"))
    k = np.linspace(0, len(xs) - 1, 9).astype(int)
    print(f"{name}: x        " + " ".join(f"{xs[i]:7.0f}" for i in k)); print(f"{name}: plan y   " + " ".join(f"{np.interp(xs[i], plan[np.argsort(plan[:, 0]), 0], plan[np.argsort(plan[:, 0]), 1]):7.1f}" for i in k))
    print(f"{name}: spine z  " + " ".join(f"{c[i, 2]:7.1f}" for i in k)); print(f"{name}: radius   " + " ".join(f"{r[i]:7.1f}" for i in k)); print(f"{name}: top z    " + " ".join(f"{c[i, 2] + r[i]:7.1f}" for i in k))
    print(f"{name}: top - surf" + " ".join(f"{(c[i, 2] + r[i] - tps(c[i:i + 1, 0], c[i:i + 1, 1])[0]):7.1f}" for i in k))
    print(f"{name}: view angles round the roll (start/mid/end): " + ", ".join(f"{ph} {v}" for ph, v in ang.items()))
