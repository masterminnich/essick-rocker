"""USAGE: uv run --no-project --with pycolmap --with numpy --with opencv-python-headless --with pillow --with scipy \
    python -I tools/square_edges.py --model work/solve/model --drive drive --out work/solve/square [--seed seed.json]
         [--window 14] [--iters 3] [--names IMG_1540.JPG,...]

Framing-square outline measurement (scale route A).
1. Seed: if --seed is absent, yellow-coloured sparse 3D points are clustered, a plane is fitted (RANSAC) and an L shape
   is fitted in the plane (body = longer leg). Nominal shape 24 x 16 in, body 2 in, tongue 1.5 in wide, used ONLY to
   place the search windows; no dimension is assumed in the measurement.
2. For every registered image the 6 outline edges are projected; along each edge, every ~3 px, the yellowness
   gradient ((R+G)/2-B, Gaussian sigma 1.2) is searched across the edge within +-window px and the maximum located to
   sub-pixel precision (parabola). Edge samples are undistorted to normalized pinhole coordinates and a robust line is
   fitted per edge (RANSAC 1.2 px then iterative least squares). Edges with too few inliers are dropped.
3. Corners = intersections of adjacent fitted 2D lines (a corner is kept for an image only if both lines are well
   supported). Each corner is triangulated over all images (DLT + Gauss-Newton); per-view residuals are reported and
   views with residual > 3 px are rejected iteratively.
4. The triangulated corners re-seed step 2 with a smaller window; repeat --iters times.
Output: <out>/corners.json (3D corners in model units, per-view 2D corners and residuals), <out>/edges/<img>.npz.
"""
import argparse, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
import rc_geom as G

INCH = 25.4
# outline vertices in (a, b) inches: a along body from outer heel, b along tongue from outer heel
VNAMES = ["O", "Bo", "Bi", "I", "Ti", "To"]
NOMINAL = np.array([[0, 0], [24, 0], [24, 2], [1.5, 2], [1.5, 16], [0, 16]], float)
EDGES = [("O", "Bo"), ("Bo", "Bi"), ("Bi", "I"), ("I", "Ti"), ("Ti", "To"), ("To", "O")]
ENAMES = ["body_outer", "body_end", "body_inner", "tongue_inner", "tongue_end", "tongue_outer"]


def seed_from_yellow(m, rng=np.random.default_rng(0)):
    ids = list(m.points3D.keys())
    X = np.array([m.points3D[i].xyz for i in ids]); C = np.array([m.points3D[i].color for i in ids], float)
    y = (C[:, 0] > 150) & (C[:, 1] > 120) & (C[:, 2] < 0.55 * C[:, 1]) & (C[:, 0] - C[:, 2] > 90)
    Y = X[y]
    # largest planar compact cluster: RANSAC planes, keep best support within 3 MAD of its median
    best = None
    scale_ref = np.median(np.linalg.norm(X - np.median(X, 0), axis=1))
    tol = 0.003 * scale_ref
    for _ in range(4000):
        s = Y[rng.choice(len(Y), 3, replace=False)]
        n = np.cross(s[1] - s[0], s[2] - s[0]); nn = np.linalg.norm(n)
        if nn < 1e-12: continue
        n /= nn
        inl = np.abs((Y - s[0]) @ n) < tol
        P = Y[inl]
        if len(P) < 30: continue
        med = np.median(P, 0); d = np.linalg.norm(P - med, axis=1)
        k = (d < 4 * np.median(d)).sum()
        if best is None or k > best[0]:
            best = (k, inl)
    P = Y[best[1]]; med = np.median(P, 0); d = np.linalg.norm(P - med, axis=1); P = P[d < 4 * np.median(d)]
    c, n, vt = G.fit_plane(P)
    e1, e2 = vt[0], vt[1]
    Q = np.c_[(P - c) @ e1, (P - c) @ e2]
    # two RANSAC lines in 2D
    lines = []
    rem = Q.copy()
    w_tol = 0.02 * np.ptp(Q[:, 0])
    for _ in range(2):
        bestl = None
        for _ in range(3000):
            i, j = rng.choice(len(rem), 2, replace=False)
            dvec = rem[j] - rem[i]; L = np.linalg.norm(dvec)
            if L < 1e-9: continue
            dvec /= L; nrm = np.array([-dvec[1], dvec[0]])
            inl = np.abs((rem - rem[i]) @ nrm) < w_tol
            if bestl is None or inl.sum() > bestl[0]:
                bestl = (inl.sum(), inl)
        pts = rem[bestl[1]]; cc = pts.mean(0); _, _, v = np.linalg.svd(pts - cc)
        lines.append((cc, v[0], pts)); rem = rem[~bestl[1]]
    # intersection of centre lines
    (c1, d1, p1), (c2, d2, p2) = lines
    A = np.c_[d1, -d2]; s12 = np.linalg.solve(A, c2 - c1); X0 = c1 + s12[0] * d1
    ext = []
    for cc, dd, pts in ((c1, d1, p1), (c2, d2, p2)):
        t = (pts - X0) @ dd
        if np.median(t) < 0: dd = -dd; t = -t
        ext.append((dd, np.percentile(t, 99)))
    (da, La), (db, Lb) = sorted(ext, key=lambda e: -e[1])
    s_unit = (La / (24 - 0.75) + Lb / (16 - 1.0)) / 2 / INCH  # model units per mm (rough)
    # (a,b) frame: centre-line intersection is at (a,b)=(0.75,1) in
    O2 = X0 - 0.75 * INCH * s_unit * da - 1.0 * INCH * s_unit * db
    to3 = lambda q: c + q[0] * e1 + q[1] * e2
    O3 = to3(O2); A3 = da[0] * e1 + da[1] * e2; B3 = db[0] * e1 + db[1] * e2
    V = {nm: O3 + (ab[0] * A3 + ab[1] * B3) * INCH * s_unit for nm, ab in zip(VNAMES, NOMINAL)}
    return V, dict(n_yellow=int(len(Y)), n_plane=int(len(P)), units_per_mm_rough=float(s_unit))


def yellowness(img):
    import cv2
    yv = (img[:, :, 0] + img[:, :, 1]) * 0.5 - img[:, :, 2]
    yv = cv2.GaussianBlur(yv, (0, 0), 1.2)
    return yv


def sample_edge(cam, yv, P0, P1, inside_dir3, window, step=3.0, margin=0.06):
    """Sample a 3D edge P0->P1; returns sub-pixel edge points (N,2) in COLMAP pixel coords."""
    import cv2
    H, W = yv.shape
    (u0, u1), z = cam.project(np.array([P0, P1]))
    if (z <= 0).any(): return np.zeros((0, 2))
    L = np.linalg.norm(u1 - u0)
    if L < 20: return np.zeros((0, 2))
    n_s = int(L / step)
    ts = np.linspace(margin, 1 - margin, max(n_s, 2))
    P = P0[None] + ts[:, None] * (P1 - P0)[None]
    uv, _ = cam.project(P)
    # local direction and inside normal via projecting offset points
    uvn, _ = cam.project(P + inside_dir3[None])
    tang = np.gradient(uv, axis=0); tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    nrm = np.c_[-tang[:, 1], tang[:, 0]]
    sgn = np.sign(np.sum((uvn - uv) * nrm, axis=1)); nrm *= sgn[:, None]  # nrm points inside (yellow)
    offs = np.arange(-window, window + 0.01, 0.5)
    out = []
    for p, nv in zip(uv, nrm):
        q = p[None] + offs[:, None] * nv[None]
        x = q[:, 0] - 0.5; y = q[:, 1] - 0.5  # COLMAP -> array index coords
        if x.min() < 2 or y.min() < 2 or x.max() > W - 3 or y.max() > H - 3: continue
        prof = cv2.remap(yv, x.astype(np.float32)[None], y.astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        g = np.gradient(prof) / 0.5  # derivative along inside direction: positive at table->yellow boundary
        k = int(np.argmax(g))
        if k < 1 or k > len(g) - 2 or g[k] < 8: continue
        # contrast check: inside must be clearly yellow
        inside = prof[min(k + 6, len(prof) - 1)]; outside = prof[max(k - 6, 0)]
        if inside - outside < 25: continue
        den = g[k - 1] - 2 * g[k] + g[k + 1]
        dk = 0.5 * (g[k - 1] - g[k + 1]) / den if den < 0 else 0.0
        out.append(p + (offs[k] + dk * 0.5) * nv)
    return np.array(out).reshape(-1, 2)


def fit_line(cam, pts, thr_px=1.2, rng=np.random.default_rng(1)):
    """Robust line in normalized coords. Returns (line homog (3,), inlier mask, rms px) or None."""
    if len(pts) < 12: return None
    f = cam.p[0]
    xn = cam.undistort(pts)
    thr = thr_px / f
    best = None
    for _ in range(300):
        i, j = rng.choice(len(xn), 2, replace=False)
        d = xn[j] - xn[i]; L = np.linalg.norm(d)
        if L < 1e-9: continue
        nv = np.array([-d[1], d[0]]) / L
        inl = np.abs((xn - xn[i]) @ nv) < thr
        if best is None or inl.sum() > best.sum(): best = inl
    inl = best
    for _ in range(5):
        c = xn[inl].mean(0); _, _, vt = np.linalg.svd(xn[inl] - c); nv = vt[1]
        r = (xn - c) @ nv
        inl_new = np.abs(r) < max(thr, 2.5 * 1.4826 * np.median(np.abs(r[inl])))
        inl_new &= np.abs(r) < 2 * thr
        if (inl_new == inl).all(): break
        inl = inl_new
    if inl.sum() < 12 or inl.sum() < 0.35 * len(xn): return None
    c = xn[inl].mean(0); _, _, vt = np.linalg.svd(xn[inl] - c); nv = vt[1]
    r = (xn[inl] - c) @ nv
    line = np.array([nv[0], nv[1], -nv @ c])
    return line, inl, float(np.sqrt(np.mean(r ** 2)) * f), xn[inl]


def measure_image(cam, img_path, V, window):
    yv = yellowness(G.load_raw(img_path))
    Vc = np.array([V[k] for k in VNAMES]); cen = Vc.mean(0)
    res = {}
    for (a, b), en in zip(EDGES, ENAMES):
        P0, P1 = V[a], V[b]
        mid = 0.5 * (P0 + P1)
        # inside direction: towards the polygon interior, in-plane, perpendicular to the edge
        e = (P1 - P0) / np.linalg.norm(P1 - P0)
        nrmp = np.cross(np.cross(Vc[1] - Vc[0], Vc[5] - Vc[0]), e); nrmp /= np.linalg.norm(nrmp)
        # choose sign so it points inside: test a point slightly inside along nrmp lies within leg width
        width = 0.4 * np.linalg.norm(V["Bi"] - V["Bo"])
        inside = nrmp * width * 0.3
        if not point_in_L(mid + inside, V): inside = -inside
        pts = sample_edge(cam, yv, P0, P1, inside, window)
        fl = fit_line(cam, pts)
        res[en] = dict(pts=pts, fit=fl)
    return res


def point_in_L(X, V):
    O = V["O"]; A = V["Bo"] - O; B = V["To"] - O
    la, lb = np.linalg.norm(A), np.linalg.norm(B); A /= la; B /= lb
    a, b = (X - O) @ A, (X - O) @ B
    wa = np.linalg.norm(V["Bi"] - V["Bo"]); wb = np.linalg.norm(V["Ti"] - V["To"])
    return (0 <= a <= la and 0 <= b <= wa) or (0 <= a <= wb and 0 <= b <= lb)


def corners_from_lines(cam, fits):
    """Intersect adjacent edge lines -> corner pixel coords."""
    out = {}
    for i, v in enumerate(VNAMES):
        e_in = ENAMES[i - 1]; e_out = ENAMES[i]
        f1, f2 = fits.get(e_in), fits.get(e_out)
        if f1 is None or f2 is None: continue
        l1, l2 = f1[0], f2[0]
        X = np.cross(l1, l2)
        if abs(X[2]) < 1e-12: continue
        xn = X[:2] / X[2]
        # angle between lines must be large enough
        c = abs(l1[:2] @ l2[:2]) / np.linalg.norm(l1[:2]) / np.linalg.norm(l2[:2])
        if c > 0.97: continue
        out[v] = cam.distort(xn[None])[0]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True); ap.add_argument("--drive", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--seed"); ap.add_argument("--window", type=float, default=14); ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--names", default="")
    ap.add_argument("--max_res", type=float, default=3.0)
    a = ap.parse_args()
    out = pathlib.Path(a.out); (out / "edges").mkdir(parents=True, exist_ok=True)
    m, cams = G.load_model(a.model)
    if a.seed:
        V = {k: np.array(v) for k, v in json.load(open(a.seed))["corners3d"].items()}; info = {}
    else:
        V, info = seed_from_yellow(m)
    print("seed", info)
    names = [n for n in sorted(cams) if (not a.names or n in a.names.split(","))]
    window = a.window
    for it in range(a.iters):
        obs = {v: [] for v in VNAMES}
        per_img = {}
        for n in names:
            cam = cams[n]
            uvV, z = cam.project(np.array([V[k] for k in VNAMES]))
            if (z <= 0).any(): continue
            inb = (uvV[:, 0] > -200) & (uvV[:, 0] < G.FULL_W + 200) & (uvV[:, 1] > -200) & (uvV[:, 1] < G.FULL_H + 200)
            if inb.sum() < 2: continue
            r = measure_image(cam, pathlib.Path(a.drive) / n, V, window)
            fits = {k: (v["fit"] if v["fit"] is not None else None) for k, v in r.items()}
            cr = corners_from_lines(cam, fits)
            per_img[n] = dict(edges={k: dict(n_pts=int(len(v["pts"])), n_inl=(int(v["fit"][1].sum()) if v["fit"] else 0),
                                              rms_px=(v["fit"][2] if v["fit"] else None),
                                              line=(v["fit"][0].tolist() if v["fit"] else None)) for k, v in r.items()},
                              corners={k: v.tolist() for k, v in cr.items()})
            np.savez(out / "edges" / (n + ".npz"), **{k: v["pts"] for k, v in r.items()})
            for k, uv in cr.items():
                if -50 < uv[0] < G.FULL_W + 50 and -50 < uv[1] < G.FULL_H + 50:
                    obs[k].append((n, uv))
        tri = {}
        for k in VNAMES:
            ob = obs[k]
            while len(ob) >= 2:
                X, res = G.triangulate(ob, cams)
                e = np.linalg.norm(res, axis=1)
                if e.max() <= a.max_res: break
                ob = [o for o, ee in zip(ob, e) if ee < e.max()]  # drop worst, repeat
            if len(ob) >= 2:
                tri[k] = dict(X=X.tolist(), views=[o[0] for o in ob], res_px=e.tolist(),
                              rms_px=float(np.sqrt(np.mean(e ** 2))), n_rejected=len(obs[k]) - len(ob))
                V[k] = X
        print(f"iter {it} window {window}: images {len(per_img)}; " +
              "; ".join(f"{k}: n={len(t['views'])} rms={t['rms_px']:.2f} rej={t['n_rejected']}" for k, t in tri.items()))
        window = max(6.0, window * 0.6)
    G.save_json(out / "corners.json", dict(model=a.model, seed_info=info, corners3d={k: V[k].tolist() for k in VNAMES},
                                         triangulation=tri, per_image=per_img))


if __name__ == "__main__":
    main()
