"""USAGE: python -I tools/curve_tri.py --trace PREFIX:PHOTO:DUMP.json:KEY[:X0:X1] [--trace ...] --x X0 X1 --guess "Y Z" | --guess-json F:KEY
            [--deg 6] [--even] [--fix-z FILE.json:KEY] [--fix-y FILE.json:KEY] [--name NAME] --out FILE.json
Triangulate ONE arris as a smooth 3D curve running across the chair, X(x) = (x, y(x), z(x)), from per-photo traces drawn on
DIFFERENT flat sheets (e.g. an overhead sheet z = const and a rear sheet y = const). Generalises tools/edge_tri.py, which keeps
one sheet and solves only a depth: here the curve is projected through each photo's camera centre onto that photo's sheet
and y(x), z(x) are fitted so the projections lie on every trace at once (robust least squares, 1 mm soft-L1 scale).
Views that cross (overhead + rear) fix both coordinates; a single direction cannot (then give --fix-z or --fix-y).
Traces: the per-photo curves written by edge_tri.py --dump ("<name>@<photo>" keys) on PREFIX_<photo>.png sheets.
:X0:X1 keeps only that part of a trace (clutter, glare). --even makes y and z even in x (design-intent, symmetric version).
--fix-z F:KEY takes z(x) from another solved curve (its "<KEY>_xyz") instead of solving it.
Output: {name_xyz: [[x,y,z]..] at 1 mm, name_info: {per-photo residual rms, coefficients, photos}}. Tiny compute."""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
from numpy.polynomial import legendre as L
from scipy.optimize import least_squares
from rocker.cameras import Cameras
from rocker.surface import load_surface

ap = argparse.ArgumentParser(); ap.add_argument("--trace", action="append", required=True); ap.add_argument("--x", nargs=2, type=float, required=True)
ap.add_argument("--guess", default=None); ap.add_argument("--guess-json", default=None); ap.add_argument("--deg", type=int, default=6); ap.add_argument("--even", action="store_true")
ap.add_argument("--fix-z", default=None); ap.add_argument("--fix-y", default=None); ap.add_argument("--name", default="curve"); ap.add_argument("--out", required=True)
ap.add_argument("--fscale", type=float, default=1.0)
a = ap.parse_args(); cams = Cameras.load(); xa, xb = a.x; xm, hw = (xa + xb) / 2, (xb - xa) / 2
if a.even: xm = 0.0; hw = max(abs(xa), abs(xb))
xs = np.arange(xa, xb + 1e-9, 1.0); s = (xs - xm) / hw
terms = [k for k in range(a.deg + 1) if (not a.even or k % 2 == 0)]
Bm = np.stack([L.legval(s, np.eye(a.deg + 1)[k]) for k in terms], 1)


def load_fixed(spec):
    f, k = spec.rsplit(":", 1); X = np.array(json.load(open(f))[k + "_xyz"]); o = np.argsort(X[:, 0]); return X[o]


traces = []
for spec in a.trace:
    parts = spec.split(":"); prefix, photo, dump, key = parts[:4]; xr = (float(parts[4]), float(parts[5])) if len(parts) >= 6 else (-1e9, 1e9)
    pj = json.load(open(prefix + "_plane.json")); S = load_surface(pj); T = np.array(json.load(open(dump))[f"{key}@{photo}"])
    T3 = S.to3d(T); keep = (T3[:, 0] >= max(xr[0], xa)) & (T3[:, 0] <= min(xr[1], xb)); T = T[keep]
    traces.append(dict(photo=photo, C=cams.views[f"IMG_{photo}.JPG"].center, o=np.array(pj["origin"]), u=np.array(pj["u"]), v=np.array(pj["v"]), n=np.array(pj["n"]), T=T[::2], sheet=Path(prefix).name))


def onsheet(tr, X):
    d = X - tr["C"]; t = ((tr["o"] - tr["C"]) @ tr["n"]) / (d @ tr["n"]); P = tr["C"] + t[:, None] * d - tr["o"]; return np.c_[P @ tr["u"], P @ tr["v"]]


def curve(p):
    k = len(terms); y = Bm @ p[:k] if not a.fix_y else np.interp(xs, FY[:, 0], FY[:, 1])
    z = (Bm @ p[:k] if a.fix_y else Bm @ p[k:2 * k]) if not a.fix_z else np.interp(xs, FZ[:, 0], FZ[:, 2])
    return np.c_[xs, y, z]


def seg_dist(Q, T):
    """signed distance of points T to polyline Q (left of the direction of travel = +)"""
    A, B = Q[:-1], Q[1:]; D = B - A; L2 = np.maximum((D ** 2).sum(1), 1e-9)
    t = np.clip(((T[:, None, :] - A[None]) * D[None]).sum(2) / L2[None], 0, 1); Pc = A[None] + t[..., None] * D[None]
    dd = np.linalg.norm(T[:, None, :] - Pc, axis=2); i = np.argmin(dd, 1); r = T - Pc[np.arange(len(T)), i]; Di = D[i]
    return np.sign(Di[:, 0] * r[:, 1] - Di[:, 1] * r[:, 0]) * dd[np.arange(len(T)), i]


def resid(p):
    X = curve(p); return np.concatenate([seg_dist(onsheet(tr, X), tr["T"]) for tr in traces])


FY = load_fixed(a.fix_y) if a.fix_y else None; FZ = load_fixed(a.fix_z) if a.fix_z else None
if a.guess_json:
    G = load_fixed(a.guess_json); gy, gz = np.interp(xs, G[:, 0], G[:, 1]), np.interp(xs, G[:, 0], G[:, 2])
else:
    g = [float(v) for v in a.guess.split()]; gy, gz = np.full(len(xs), g[0]), np.full(len(xs), g[1])
p0 = []
if not a.fix_y: p0 += list(np.linalg.lstsq(Bm, gy, rcond=None)[0])
if not a.fix_z: p0 += list(np.linalg.lstsq(Bm, gz, rcond=None)[0])
r = least_squares(resid, np.array(p0), loss="soft_l1", f_scale=a.fscale, x_scale=5.0)
X = curve(r.x); info = {"photos": [], "x_range": [xa, xb], "deg": a.deg, "even": a.even, "fixed": {"y": a.fix_y, "z": a.fix_z}}
for tr in traces:
    e = seg_dist(onsheet(tr, X), tr["T"]); info["photos"].append({"photo": tr["photo"], "sheet": tr["sheet"], "n": int(len(e)), "rms_mm": float(np.sqrt(np.mean(e ** 2))),
                                                                  "median_mm": float(np.median(e)), "inlier_rms_mm": float(np.sqrt(np.mean(e[np.abs(e) < 2.5] ** 2))) if (np.abs(e) < 2.5).any() else None, "outlier_share": float(np.mean(np.abs(e) >= 2.5))})
# 1-sigma of the curve from the Jacobian at the solution (inliers only), mapped to y and z
J = r.jac; res_ = r.fun; w = np.abs(resid(r.x)) < 2.5; k = len(terms)
try:
    cov = np.linalg.inv(J[w].T @ J[w]) * np.mean(res_[w] ** 2) * len(res_[w]) / max(1, w.sum() - len(r.x))
    blocks = []
    if not a.fix_y: blocks.append(("y", slice(0, k)))
    if not a.fix_z: blocks.append(("z", slice(k if not a.fix_y else 0, k + (k if not a.fix_y else 0))))
    for nm, sl in blocks: info[f"sigma_{nm}_mm"] = {"max": float(np.sqrt(np.max(np.einsum("ij,jk,ik->i", Bm, cov[sl, sl], Bm)))), "mid": float(np.sqrt(np.einsum("ij,jk,ik->i", Bm, cov[sl, sl], Bm)[len(xs) // 2]))}
except np.linalg.LinAlgError: pass
info["coef_legendre"] = {"terms": terms, "x_mid": xm, "x_half": hw, "p": r.x.tolist()}
json.dump({a.name + "_xyz": X.tolist(), a.name + "_info": info}, open(a.out, "w"))
print(f"{a.name}: y {X[0,1]:.1f} / {X[len(X)//2,1]:.1f} / {X[-1,1]:.1f}  z {X[0,2]:.1f} / {X[len(X)//2,2]:.1f} / {X[-1,2]:.1f} (start/mid/end)  " +
      " | ".join(f"{p['photo']} {p['inlier_rms_mm']:.2f} ({100*p['outlier_share']:.0f}% out)" for p in info["photos"]) +
      "".join(f" | sigma_{c} max {info[f'sigma_{c}_mm']['max']:.2f}" for c in "yz" if f"sigma_{c}_mm" in info))
