"""USAGE: python -I tools/face_ortho.py --point X Y Z --normal NX NY NZ --urange A B --vrange C D [--res 0.5]
            [--offset 0] [--tilt 0] [--yaw 0] [--photos auto|1503,1504] [--max-angle 60] [--max-photos 8] --out PREFIX
            [--sweep offset|tilt|yaw A B STEP]
Rectify several photos onto one plane of the chair ("face orthophotos") and combine them.
The plane passes through POINT with outward NORMAL (chair frame, mm). In-plane axes: u = horizontal, v = up-ish.
The plane origin is moved along u,v to the point of the plane nearest chair y=0,z=0 so u ~ chair Y for side faces.
--offset moves the plane along its normal (mm), --tilt rotates it about u, --yaw about v (deg).
Outputs PREFIX_<photo>.png (each photo rectified), PREFIX_median.png (per-pixel median: things ON the plane stay sharp,
everything off the plane smears), PREFIX_spread.png (per-pixel disagreement between photos; dark = consistent = on plane).
--sweep varies one plane parameter and prints a photo-consistency score per value (lower = better aligned), which
locates the true face plane without trusting the point cloud.
Compute: one photo decoded at a time (36 MB); orthos are small (e.g. 2400 x 300 px). < 1 GB, seconds.
"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from rocker.cameras import Cameras
from rocker.ortho import Plane, ortho, load_raw

ap = argparse.ArgumentParser()
ap.add_argument("--point", nargs=3, type=float, required=True); ap.add_argument("--normal", nargs=3, type=float, required=True)
ap.add_argument("--urange", nargs=2, type=float, required=True); ap.add_argument("--vrange", nargs=2, type=float, required=True)
ap.add_argument("--res", type=float, default=0.5); ap.add_argument("--offset", type=float, default=0); ap.add_argument("--tilt", type=float, default=0)
ap.add_argument("--yaw", type=float, default=0); ap.add_argument("--photos", default="auto"); ap.add_argument("--max-angle", type=float, default=60)
ap.add_argument("--max-photos", type=int, default=8); ap.add_argument("--out", required=True); ap.add_argument("--sweep", nargs=4, default=None)
ap.add_argument("--optimize", action="store_true", help="refine offset, tilt, yaw together by photo consistency, then write outputs")
ap.add_argument("--u-axis", nargs=3, type=float, default=None, help="in-plane u direction hint (default: horizontal)")
a = ap.parse_args()
cams = Cameras.load()


def rot(axis, deg):
    axis = axis / np.linalg.norm(axis); t = np.radians(deg); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K


def make_plane(offset, tilt, yaw):
    n = np.array(a.normal, float); n /= np.linalg.norm(n); p = np.array(a.point, float)
    if a.u_axis is not None:
        u = np.array(a.u_axis, float)
    else:
        u = np.cross([0, 0, 1.0], n)
        if np.linalg.norm(u) < 1e-6: u = np.array([1.0, 0, 0])
        if abs(u[1]) > abs(u[0]) and u[1] < 0: u = -u
        if abs(u[0]) >= abs(u[1]) and u[0] < 0: u = -u
    u = u - n * (u @ n); u /= np.linalg.norm(u)
    v = np.cross(n, u)
    if v[2] < 0 or (abs(v[2]) < 1e-6 and v[1] < 0): v = -v
    Rm = rot(v, yaw) @ rot(u, tilt)
    n2, u2, v2 = Rm @ n, Rm @ u, Rm @ v
    o = p + n2 * offset
    i, j = int(np.argmax(np.abs(u2))), int(np.argmax(np.abs(v2)))      # slide the origin in-plane to chair-axis zero
    if i != j:
        ab = np.linalg.solve(np.array([[u2[i], v2[i]], [u2[j], v2[j]]]), -np.array([o[i], o[j]]))
        o = o + ab[0] * u2 + ab[1] * v2
    return Plane(o, u2, v2), n2


def pick_photos(pl, n):
    if a.photos != "auto":
        return [f"IMG_{x}.JPG" for x in a.photos.split(",")]
    cen = pl.to3d([[np.mean(a.urange), np.mean(a.vrange)]])[0]
    corners = pl.to3d([[a.urange[0], a.vrange[0]], [a.urange[1], a.vrange[0]], [a.urange[0], a.vrange[1]], [a.urange[1], a.vrange[1]]])
    cand = []
    for name, vw in cams.views.items():
        d = vw.center - cen; dist = np.linalg.norm(d); ang = np.degrees(np.arccos(np.clip(d @ n / dist, -1, 1)))
        if ang > a.max_angle or dist > 3200 or dist < 500: continue
        uv = vw.project(corners)
        if not vw.in_image(uv, margin=-20).all(): continue
        cand.append((ang, name))
    return [nm for _, nm in sorted(cand)[:a.max_photos]]


def stack(pl, photos, raws):
    return [ortho(cams, nm, pl, a.urange, a.vrange, a.res, raw=raws[nm]) for nm in photos]


def norm_gray(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    hp = g - cv2.GaussianBlur(g, (0, 0), 6 / a.res)            # remove shading / gloss gradients at > 6 mm scale
    sd = np.sqrt(cv2.GaussianBlur(hp * hp, (0, 0), 6 / a.res)) + 2.0
    return hp / sd


def score(ims):
    G = np.stack([norm_gray(i) for i in ims]); valid = np.all(np.stack([i.sum(2) > 0 for i in ims]), 0)
    sp = G.std(0); sp[~valid] = np.nan
    vals = np.sort(sp[valid]); k = max(1, int(0.3 * len(vals)))
    return float(vals[:k].mean()), sp


pl0, n0 = make_plane(a.offset, a.tilt, a.yaw)
photos = pick_photos(pl0, n0)
print("photos:", " ".join(p[4:8] for p in photos))
raws = {nm: load_raw(cams, nm) for nm in photos}          # <= 8 photos x 36 MB
if a.optimize:
    from scipy.optimize import minimize
    f = lambda p: score(stack(make_plane(p[0], p[1], p[2])[0], photos, raws))[0]
    x0 = np.array([a.offset, a.tilt, a.yaw])
    r = minimize(f, x0, method="Nelder-Mead", options={"initial_simplex": x0 + np.array([[0, 0, 0], [2, 0, 0], [0, 0.6, 0], [0, 0, 0.4]]),
                                                      "xatol": 0.05, "fatol": 2e-5, "maxiter": 120})
    a.offset, a.tilt, a.yaw = map(float, r.x)
    print(f"optimised: offset {a.offset:.2f} mm, tilt {a.tilt:.2f} deg, yaw {a.yaw:.2f} deg, score {r.fun:.4f} (start {f(x0):.4f}), evals {r.nfev}")
    for d, nm in (([0.5, 0, 0], "offset +0.5 mm"), ([-0.5, 0, 0], "offset -0.5 mm"), ([0, 0.3, 0], "tilt +0.3"), ([0, 0, 0.15], "yaw +0.15")):
        print("   ", nm, "-> score", round(f(r.x + d), 4))
    pl0, n0 = make_plane(a.offset, a.tilt, a.yaw)
if a.sweep:
    what, lo, hi, st = a.sweep[0], float(a.sweep[1]), float(a.sweep[2]), float(a.sweep[3])
    for val in np.arange(lo, hi + 1e-9, st):
        kw = dict(offset=a.offset, tilt=a.tilt, yaw=a.yaw); kw[what] = val
        pl, _ = make_plane(**kw); s, _ = score(stack(pl, photos, raws))
        print(f"{what} {val:7.2f}  score {s:.4f}")
else:
    ims = stack(pl0, photos, raws)
    for nm, im in zip(photos, ims): cv2.imwrite(f"{a.out}_{nm[4:8]}.png", im)
    med = np.median(np.stack(ims), 0).astype(np.uint8); cv2.imwrite(f"{a.out}_median.png", med)
    s, sp = score(ims); spv = np.nan_to_num(sp, nan=2.0); cv2.imwrite(f"{a.out}_spread.png", np.clip(spv * 160, 0, 255).astype(np.uint8))
    json.dump({"origin": pl0.origin.tolist(), "u": pl0.u.tolist(), "v": pl0.v.tolist(), "n": n0.tolist(), "urange": a.urange, "vrange": a.vrange,
               "res": a.res, "photos": photos, "score": s, "offset": a.offset, "tilt": a.tilt, "yaw": a.yaw}, open(f"{a.out}_plane.json", "w"), indent=1)
    print("score", round(s, 4), "size", med.shape)
