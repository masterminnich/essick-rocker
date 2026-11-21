"""USAGE: work/toolkit/rk.sh tools/seat_scoop/solve.py SIDE(L|R) CFG.json OUT.json [DEG 5]      (parts/seat_scoop.json: R tools/seat_scoop/inputs/solve.json work/seat_scoop/solved_R.json 6)
Step 3 of 4. Triangulates the two edges of the seat side scoop as smooth 3D curves P(y) = (x(y), y, z(y)) from per-photo traces.
CFG.json: {"traces": ["a_px.json", ...], "use": {"crescent": {"1488": [[170, 440]], ...}, "bottom": {...}}, "y": {"crescent": [ya, yb], "bottom": [ya, yb]}}
  traces: files written by snap.py (displayed pixels per station y; keys "<curve>*@<photo>"); use: per curve and photo, the station
  ranges of the trace that are trusted (checked by eye on the unrolled strip).
Fit: x(y), z(y) Legendre polynomials of degree DEG; residual = signed distance in the photo from the projected curve to the traced
polyline, divided by the local pixels per mm square to the line of sight (so in mm at the edge), soft-L1 0.5 mm. Samples every 5 mm; a sample whose nearest
trace point is the END of a trusted piece is left out in that photo.
CFG "init": {curve: [file, key]} starts from an earlier solution (needed when traces from ALT strips are in: their t is not between the arrises).
Prints per-photo residuals and leave-one-photo-out changes; writes {curve: {"xyz": [[x, y, z] every mm], "photos": {...}, "leave_one_out_mm": .., "loo_xyz": {photo: the curve solved without it}}}.
SIDE L: tools/seat_scoop/inputs_L/solve.json -> work/seat_scoop_L/solved_L.json (left-side check, tools/seat_scoop/compare_lr.py)."""
import sys, json, numpy as np
sys.path.insert(0, ".")
from numpy.polynomial import legendre as L
from scipy.optimize import least_squares
from rocker.cameras import Cameras
side, cfgf, outf = sys.argv[1:4]; DEG = int(sys.argv[4]) if len(sys.argv) > 4 else 5
c = Cameras.load(); cfg = json.load(open(cfgf)); E = json.load(open("parts/seat_edge.json"))[{"L": "left", "R": "right"}[side]]
T = np.array(E["top_arris_side_xyz"]); B = np.array(E["bottom_arris_xyz"]); T = T[np.argsort(T[:, 1])]; B = B[np.argsort(B[:, 1])]
def at(A, y):
    y = np.atleast_1d(np.asarray(y, float)); out = np.stack([np.interp(y, A[:, 1], A[:, i]) for i in range(3)], 1)
    for lo, sel in ((True, A[:, 1] < A[0, 1] + 60), (False, A[:, 1] > A[-1, 1] - 60)):
        m = (y < A[0, 1]) if lo else (y > A[-1, 1])
        if m.any():
            for i in (0, 2): out[m, i] = np.polyval(np.polyfit(A[sel, 1], A[sel, i], 1), y[m])
            out[m, 1] = y[m]
    return out
TRC = {}
for f in cfg["traces"]: TRC.update(json.load(open(f)))
YT = {}
for f in cfg["traces"]: YT.update(json.load(open(f.replace("_px.json", "_yt.json"))))
OUT = {}
import os
ONLY = os.environ.get("ONLY")
for curve, use in cfg["use"].items():
    if ONLY: use = {k: v for k, v in use.items() if k in ONLY.split(",")}
    ya, yb = cfg["y"][curve]; ym, hw = (ya + yb) / 2, (yb - ya) / 2; yk = np.arange(ya, yb + 1e-9, 5.0); sk = (yk - ym) / hw
    Bm = np.stack([L.legval(sk, np.eye(DEG + 1)[k]) for k in range(DEG + 1)], 1)
    pieces = {}; tmean = []
    for n, ranges in use.items():
        segs = []
        for key in TRC:
            if key.startswith(curve) and key.endswith("@" + n):
                uv = np.array(TRC[key]); yy = np.array(YT[key])
                for a, b in ranges:
                    m = (yy[:, 0] >= a) & (yy[:, 0] <= b)
                    if m.sum() > 5 and (len(ranges) == 1 or True): segs.append(uv[m]); tmean.append(yy[m])
        # a photo may have two trace keys (main + re-seeded end): where trusted ranges overlap the later key simply adds a second piece
        pieces[n] = segs
    tm = np.concatenate(tmean); o = np.argsort(tm[:, 0]); tk = np.interp(yk, tm[o, 0], np.convolve(tm[o, 1], np.ones(9) / 9, "same"))
    P0 = at(T, yk) + tk[:, None] * (at(B, yk) - at(T, yk)); ch = at(B, yk) - at(T, yk); ch /= np.linalg.norm(ch, axis=1)[:, None]
    if cfg.get("init", {}).get(curve):      # start from an earlier solution (needed when some traces come from ALT strips: their t is not between the two arrises)
        _f, _k = cfg["init"][curve]; _I = np.array(json.load(open(_f))[_k]["xyz"]); P0 = np.c_[np.interp(yk, _I[:, 1], _I[:, 0]), yk, np.interp(yk, _I[:, 1], _I[:, 2])]
    p0 = np.r_[np.linalg.lstsq(Bm, P0[:, 0], rcond=None)[0], np.linalg.lstsq(Bm, P0[:, 2], rcond=None)[0]]
    def curve_xyz(p, Bmat=Bm, y=yk): return np.c_[Bmat @ p[:DEG + 1], y, Bmat @ p[DEG + 1:]]
    def resid_photo(P, n):
        name = f"IMG_{n}.JPG"; uv = c.project_disp(name, P); ray = P - np.asarray(c.views[name].center, float); ray /= np.linalg.norm(ray, axis=1)[:, None]
        nn = np.cross(np.array([0.0, 1.0, 0.0]), ray); nn /= np.linalg.norm(nn, axis=1)[:, None]      # square to the edge's run and to the line of sight
        s = np.linalg.norm(c.project_disp(name, P + nn) - uv, axis=1)   # px per mm across the edge as this photo sees it (the old-wall chord was used before: wrong for steep photos, which look along it)
        best = np.full(len(P), 1e9); val = np.zeros(len(P)); ok = np.zeros(len(P), bool)
        for seg in pieces[n]:
            a, b = seg[:-1], seg[1:]; ab = b - a; l2 = (ab ** 2).sum(1)
            w = ((uv[:, None, :] - a[None]) * ab[None]).sum(2) / l2[None]; wc = np.clip(w, 0, 1); q = a[None] + wc[:, :, None] * ab[None]
            d = np.linalg.norm(uv[:, None, :] - q, axis=2); j = d.argmin(1); i = np.arange(len(P)); dj = d[i, j]
            sg = np.sign(ab[j, 0] * (uv[:, 1] - a[j, 1]) - ab[j, 1] * (uv[:, 0] - a[j, 0])); inside = ~(((j == 0) & (w[i, j] <= 0)) | ((j == len(a) - 1) & (w[i, j] >= 1)))
            upd = dj < best; best[upd] = dj[upd]; val[upd] = (sg * dj / s)[upd]; ok[upd] = inside[upd]
        return val, ok
    def fun(p, photos):
        P = curve_xyz(p); r = []
        for n in photos:
            v, ok = resid_photo(P, n); r.append(np.where(ok, v, 0.0))
        return np.concatenate(r)
    photos = list(use)
    def solve(photos): return least_squares(fun, p0, args=(photos,), loss="soft_l1", f_scale=0.5, x_scale=np.r_[np.ones(DEG + 1), np.ones(DEG + 1)]).x
    p = solve(photos); P = curve_xyz(p); info = {}
    print(f"== {curve}  y {ya}-{yb}  degree {DEG}")
    for n in photos:
        v, ok = resid_photo(P, n); info[n] = {"rms_mm": round(float(np.sqrt(np.mean(v[ok] ** 2))), 2), "mean_mm": round(float(v[ok].mean()), 2), "samples": int(ok.sum()), "y": [float(yk[ok].min()), float(yk[ok].max())]}
        _d = np.asarray(c.views[f"IMG_{n}.JPG"].center, float) - P[len(P) // 2]; info[n]["camera_elevation_deg"] = round(float(np.degrees(np.arctan2(_d[2], np.hypot(_d[0], _d[1])))), 1)
        print(f"   {n}: rms {info[n]['rms_mm']:.2f} mm  mean {info[n]['mean_mm']:+.2f}  n {ok.sum():3d}  y {yk[ok].min():.0f}-{yk[ok].max():.0f}   elevation {info[n]['camera_elevation_deg']:+.1f}   camera {np.round(c.views[f'IMG_{n}.JPG'].center).astype(int).tolist()}")
    loo = {}; loo_p = {}
    for n in photos:
        loo_p[n] = solve([m for m in photos if m != n]); q = curve_xyz(loo_p[n]); dd = np.linalg.norm(q - P, axis=1); mid = (yk > ya + 40) & (yk < yb - 40); loo[n] = [round(float(dd[mid].max()), 2), round(float(dd.max()), 2)]
        print(f"   without {n}: curve moves by up to {loo[n][0]:.2f} mm (inner part), {loo[n][1]:.2f} mm (whole)")
    y1 = np.arange(ya, yb + 1e-9, 1.0); B1 = np.stack([L.legval((y1 - ym) / hw, np.eye(DEG + 1)[k]) for k in range(DEG + 1)], 1); P1 = curve_xyz(p, B1, y1)
    Tc, Bc = at(T, y1), at(B, y1); chd = Bc - Tc; ln = np.linalg.norm(chd[:, [0, 2]], axis=1); nrm = np.c_[-chd[:, 2], chd[:, 0]] / ln[:, None]      # outward normal of the old wall in the section plane
    offw = ((P1[:, [0, 2]] - Tc[:, [0, 2]]) * nrm).sum(1); along = ((P1[:, [0, 2]] - Tc[:, [0, 2]]) * chd[:, [0, 2]]).sum(1) / ln
    for y in range(int(ya // 50 * 50 + 50), int(yb), 50):
        i = int(y - ya); print(f"   y {y}: x {P1[i, 0]:.1f} z {P1[i, 2]:.1f}   top arris x {Tc[i, 0]:.1f} z {Tc[i, 2]:.1f}   old bottom x {Bc[i, 0]:.1f} z {Bc[i, 2]:.1f}   off the old wall {offw[i]:+.1f} mm, {along[i]:.1f} of {ln[i]:.1f} mm down it")
    OUT[curve] = {"loo_xyz": {n: curve_xyz(v, B1, y1).round(2).tolist() for n, v in loo_p.items()},      # the curve solved without each photo (jackknife; tools/seat_scoop/compare_lr.py)
                  "xyz": P1.round(2).tolist(), "photos": info, "leave_one_out_mm": loo, "off_old_wall_mm": offw.round(2).tolist(), "degree": DEG}
json.dump(OUT, open(outf, "w")); print("wrote", outf)
