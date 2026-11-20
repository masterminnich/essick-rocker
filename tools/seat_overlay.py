"""USAGE: tools/py.sh -m 2 -t 5 tools/seat_overlay.py IMG_1604 [IMG_...]
The measured seat surface (seat/surface.json: thin-plate formula, both halves) drawn over a dot photo:
translucent colour = depth below rim (light = rim, dark blue = deep), black lines = depth contours every 5 mm,
white lines = 20 mm grid in x and y, cyan = the dots (mirrored dots hollow). Surface self-occlusion by painter's
algorithm; chair parts in front of the seat (arms, posts) are NOT masked, the overlay paints over them.
-> seat/figures/overlay_<name>.jpg (half size, displayed orientation). Compute: < 400 MB, a few s per photo."""
import sys, json, csv; from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from PIL import Image
from scipy.spatial import Delaunay
import contourpy
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from rocker.seatcams import load
from rocker.orientation import exif_orientation

S = json.load(open(ROOT / "seat/surface.json")); tp = S["tps"]
Cn, W, A = np.array(tp["centres"]), np.array(tp["w"]), np.array(tp["a"])
def surf(x, y):
    P = np.c_[np.ravel(x), np.ravel(y)]; r = np.linalg.norm(P[:, None] - Cn[None], axis=2)
    k = np.where(r > 0, r ** 2 * np.log(np.maximum(r, 1e-12)), 0.0)
    return (k @ W + A[0] + A[1] * P[:, 0] + A[2] * P[:, 1]).reshape(np.shape(x))
zr = lambda y: np.interp(y, S["rim"]["y"], S["rim"]["z"])
hull = Delaunay(Cn)
h = 4.0
gx, gy = np.meshgrid(np.arange(-252, 253, h), np.arange(62, 532, h))
ins = (hull.find_simplex(np.c_[gx.ravel(), gy.ravel()]) >= 0).reshape(gx.shape)
gz = surf(gx, gy); D = zr(gy) - gz
near = ins.copy()                                    # cells touching the measured region (edge clipped by a mask below)
near[:-1] |= ins[1:]; near[1:] |= ins[:-1]; near[:, :-1] |= near[:, 1:].copy(); near[:, 1:] |= near[:, :-1].copy()
Dc = D.copy(); Dc[~ins] = np.nan
# measured-region boundary: convex hull of the (mirrored) dots, densified every 2 mm, lifted onto the surface
hv = Cn[hull.convex_hull[:, 0]]; from scipy.spatial import ConvexHull; ch = ConvexHull(Cn); B = Cn[ch.vertices]
B = np.vstack([np.linspace(B[k], B[(k + 1) % len(B)], max(2, int(np.linalg.norm(B[(k + 1) % len(B)] - B[k]) / 2)), endpoint=False) for k in range(len(B))])
B3 = np.c_[B, surf(B[:, 0], B[:, 1])]
dmax = 26.0
cmap = plt.cm.Blues
R = list(csv.DictReader(open(ROOT / "seat/dots.csv")))
X = np.array([[float(r[k]) for k in ("x_mm", "y_mm", "z_mm")] for r in R])
Xm = X[np.abs(X[:, 0]) > 3] * [-1, 1, 1]
cg = contourpy.contour_generator(gx, gy, np.ma.masked_invalid(Dc))
cams = load()
def proj(v, P, s):
    """pixels (scaled by s); NaN for points behind the camera or outside a 15% margin around the frame
    (the distortion polynomial folds far-off-frame points back into the image)."""
    P = np.atleast_2d(P); C = v.to_cam(P); z = C[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"): xn = C[:, :2] / z[:, None]
    f = v.focal_raw; lim = np.array([2016, 1512]) * 1.15 / f
    ok = (z > 0) & (np.abs(xn[:, 0]) < lim[0]) & (np.abs(xn[:, 1]) < lim[1])
    uv = np.full((len(P), 2), np.nan); uv[ok] = v.project(P[ok]) * s
    return uv, z

for n in sys.argv[1:]:
    n = n if n.endswith(".JPG") else n + ".JPG"; v = cams[n]
    im = Image.open(cams.drive / n); im.draft("RGB", (2016, 1512)); im = np.asarray(im.convert("RGB"))[:, :, ::-1].copy()
    s = im.shape[1] / 4032
    P3 = np.c_[gx.ravel(), gy.ravel(), gz.ravel()]
    ok = np.ones(len(P3), bool); uv = np.full((len(P3), 2), np.nan); dep = np.full(len(P3), np.nan)
    uv, dep = proj(v, P3, s)
    uv = uv.reshape(gx.shape + (2,)); dep = dep.reshape(gx.shape)
    lay = im.copy(); quads = []
    for i in range(gx.shape[0] - 1):
        for j in range(gx.shape[1] - 1):
            c = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
            if not all(near[a] for a in c) or not all(np.isfinite(uv[a]).all() for a in c): continue
            quads.append((np.mean([dep[a] for a in c]), i, j))
    quads.sort(reverse=True)                          # far first (painter's algorithm)
    for _, i, j in quads:
        poly = np.array([uv[i, j], uv[i, j + 1], uv[i + 1, j + 1], uv[i + 1, j]])
        dd = np.nanmean([D[i, j], D[i, j + 1], D[i + 1, j + 1], D[i + 1, j]])
        col = np.array(cmap(0.15 + 0.85 * np.clip(dd / dmax, 0, 1))[:3])[::-1] * 255
        cv2.fillConvexPoly(lay, np.round(poly * 16).astype(np.int32), col.tolist(), cv2.LINE_AA, 4)
    mask = np.zeros(im.shape[:2], np.uint8); qb = proj(v, B3, s)[0]
    whole = np.isfinite(qb).all()
    if whole: cv2.fillPoly(mask, [np.round(qb * 16).astype(np.int32)], 255, cv2.LINE_AA, 4)
    else:     # boundary leaves the field of view: mask = cells fully inside the measured region
        for _, i, j in quads:
            if ins[i, j] and ins[i, j + 1] and ins[i + 1, j + 1] and ins[i + 1, j]:
                poly = np.array([uv[i, j], uv[i, j + 1], uv[i + 1, j + 1], uv[i + 1, j]])
                cv2.fillConvexPoly(mask, np.round(poly * 16).astype(np.int32), 255, cv2.LINE_AA, 4)
    a = (mask.astype(np.float32) / 255 * 0.5)[..., None]
    im = (lay * a + im * (1 - a)).astype(np.uint8)
    if whole: cv2.polylines(im, [np.round(qb * 16).astype(np.int32)], True, (255, 255, 255), 2, cv2.LINE_AA, 4)
    def line3(P, colr, th):
        P = P[np.isfinite(P[:, 2])]
        if len(P) < 2: return
        q = proj(v, P, s)[0]; good = np.isfinite(q).all(1)
        for seg in np.split(np.arange(len(q)), np.flatnonzero(np.diff(good.astype(int))) + 1):
            if good[seg[0]] and len(seg) > 1:
                cv2.polylines(im, [np.round(q[seg] * 16).astype(np.int32)], False, colr, th, cv2.LINE_AA, 4)
    for g0 in range(-240, 241, 20):                    # grid
        yy = np.arange(62, 532, 2.0); m = hull.find_simplex(np.c_[np.full_like(yy, g0), yy]) >= 0
        if m.sum() > 1: line3(np.c_[np.full(m.sum(), g0), yy[m], surf(np.full(m.sum(), g0), yy[m])], (235, 235, 235), 1)
    for g0 in range(80, 531, 20):
        xx = np.arange(-252, 253, 2.0); m = hull.find_simplex(np.c_[xx, np.full_like(xx, g0)]) >= 0
        if m.sum() > 1: line3(np.c_[xx[m], np.full(m.sum(), g0), surf(xx[m], np.full(m.sum(), g0))], (235, 235, 235), 1)
    for lev in range(5, 26, 5):                         # depth contours
        for L in cg.lines(lev):
            if len(L) > 1: line3(np.c_[L, surf(L[:, 0], L[:, 1])], (20, 20, 20), 2)
    for P, fill in ((X, True), (Xm, False)):
        q = proj(v, P, s)[0]
        for p in q[np.isfinite(q).all(1)]:
            if 0 <= p[0] < im.shape[1] and 0 <= p[1] < im.shape[0]:
                cv2.circle(im, tuple(np.round(p).astype(int)), 4, (255, 255, 0), -1 if fill else 1, cv2.LINE_AA)
    img = Image.fromarray(im[:, :, ::-1]); tr = {3: Image.ROTATE_180, 6: Image.ROTATE_270, 8: Image.ROTATE_90}.get(exif_orientation(str(cams.drive / n)))
    if tr is not None: img = img.transpose(tr)
    out = ROOT / f"seat/figures/overlay_{n[:-4]}.jpg"; img.save(out, quality=82); print(n, "->", out.name, img.size)
