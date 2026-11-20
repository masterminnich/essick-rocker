"""USAGE:
  tools/py.sh -m 2 -t 10 tools/seat_dots.py detect [IMG_1595 ...]   # default: every registered dot photo
  tools/py.sh -m 2 -t 5  tools/seat_dots.py dots [--merge 9] [--maxerr 3]
Blue-tape seat dots -> 3D.
detect: per registered dot photo (rocker.seatcams), full-res raw pixels, ONE photo in memory at a time:
        blue mask in HSV (H 95-130 of 180, S > 90, V > 50) inside the projected seat region (seat cloud points dilated),
        connected components (area >= 12 px), sub-pixel centroid weighted by blueness. -> work/seat/det/<name>.npz,
        check image work/seat/det/<name>.jpg (half size, displayed orientation, detections ringed and numbered).
dots:   seeds from every photo pair (angle > 8 deg): detections in q within 4 px of the projected ray segment of a
        detection in p (inside the seat box) -> two-view point -> gather the nearest detection in every photo (4 px, then
        --maxerr px; unambiguous = 2nd nearest > 2R) -> greedy acceptance by support (most photos first, no detection
        used twice). Each kept point: multi-view triangulation (least squares on rays),
        then Gauss-Newton on reprojection error, observations above --maxerr px dropped, >= 3 photos kept.
        Per-dot 1-sigma uncertainty from the reprojection Jacobian scaled by max(residual rms, 0.5 px).
        -> seat/dots.csv (id, x, y, z mm chair frame, sx, sy, sz, s_normal mm, n_photos, rms_px, max_angle_deg, photos)
Compute audit: detect ~ 36 MB photo + 3 masks ~ 300 MB peak, ~2-4 s/photo, 2 threads. dots: tiny (<200 MB, seconds).
"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from PIL import Image
from rocker.seatcams import load

DET = ROOT / "work/seat/det"; DET.mkdir(parents=True, exist_ok=True)
seat_z = lambda y: 338 + 0.155 * y      # rough seat rim plane (tools/build_model.py)


def seat_cloud():
    C = np.load(ROOT / "work/dense/chair_dense.npy")[:, :3]
    m = (np.abs(C[:, 0]) < 290) & (C[:, 1] > -60) & (C[:, 1] < 580) & (C[:, 2] > seat_z(C[:, 1]) - 22) & (C[:, 2] < seat_z(C[:, 1]) + 45)
    return C[m]


def prior_surface():
    S = seat_cloud(); S = S[S[:, 2] > seat_z(S[:, 1]) - 16]
    f = lambda x, y: np.stack([(x / 250.) ** i * ((y - 250.) / 250.) ** j for i in range(5) for j in range(5) if i + j <= 5], 1)
    keep = np.ones(len(S), bool)
    for _ in range(6):
        c = np.linalg.lstsq(f(S[keep, 0], S[keep, 1]), S[keep, 2], rcond=None)[0]; r = S[:, 2] - f(S[:, 0], S[:, 1]) @ c
        keep = np.abs(r) < 4
    print("prior surface rms %.2f mm on %d pts" % (np.sqrt((r[keep] ** 2).mean()), keep.sum()))
    return lambda x, y: f(np.atleast_1d(x), np.atleast_1d(y)) @ c


def cmd_detect(names):
    cv2.setNumThreads(2); cams = load()
    names = names or sorted(n for n in json.loads((ROOT / "work/seat/poses.json").read_text()) if n in cams.views)
    S = seat_cloud()
    for n in names:
        n = n if n.endswith(".JPG") else n + ".JPG"; v = cams[n]
        rgb = np.asarray(Image.open(cams.drive / n).convert("RGB"))          # raw sensor orientation
        uv = v.project(S); ok = v.in_image(uv)
        reg = np.zeros(rgb.shape[:2], np.uint8)
        if ok.sum() > 50:
            hull = cv2.convexHull(uv[ok].astype(np.float32)).astype(np.int32); cv2.fillConvexPoly(reg, hull, 255)
            reg = cv2.dilate(reg, np.ones((61, 61), np.uint8))
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        H, Sat, V = hsv[..., 0].astype(np.int16), hsv[..., 1], hsv[..., 2]
        mask = ((H >= 95) & (H <= 130) & (Sat > 90) & (V > 50)).astype(np.uint8) * 255
        mask &= reg; mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        blue = np.clip(rgb[..., 2].astype(np.float32) - rgb[..., 0], 0, None)
        nl, lab, st, cen = cv2.connectedComponentsWithStats(cv2.dilate(mask, np.ones((7, 7), np.uint8)), 8)
        lab = lab * (mask > 0)                      # pieces of one tape split by glare (gap < ~6 px) share a label
        out = []
        for k in range(1, nl):
            x, y, w, h, _ = st[k]; a = int((lab[y:y + h, x:x + w] == k).sum())
            if a < 12: continue
            sub = (lab[y:y + h, x:x + w] == k) * blue[y:y + h, x:x + w]; tot = sub.sum()
            yy, xx = np.mgrid[y:y + h, x:x + w]
            cx, cy = (sub * xx).sum() / tot, (sub * yy).sum() / tot
            # shape: second moments -> major/minor axis (px)
            m = lab[y:y + h, x:x + w] == k; X = np.c_[xx[m] - cx, yy[m] - cy]; ev = np.sqrt(np.maximum(np.linalg.eigvalsh(np.cov(X.T)), 0)) * 4 if a > 3 else [0, 0]
            out.append([cx, cy, a, ev[1], ev[0]])
        out = np.array(out).reshape(-1, 5)
        np.savez(DET / (n[:-4] + ".npz"), uv=out[:, :2], area=out[:, 2], major=out[:, 3], minor=out[:, 4])
        # check image: half size, displayed orientation
        bgr = cv2.cvtColor(rgb[::2, ::2], cv2.COLOR_RGB2BGR).copy(); del rgb, hsv, H, Sat, V, blue, lab
        for i, (cx, cy, *_ ) in enumerate(out):
            p = (int(cx / 2), int(cy / 2)); cv2.circle(bgr, p, 9, (0, 255, 255), 2); cv2.putText(bgr, str(i), (p[0] + 8, p[1] - 6), 0, 0.5, (0, 255, 255), 1)
        img = Image.fromarray(bgr[..., ::-1]); img.info["exif"] = None
        from rocker.orientation import exif_orientation
        o = exif_orientation(str(cams.drive / n))
        tr = {3: Image.ROTATE_180, 6: Image.ROTATE_270, 8: Image.ROTATE_90}.get(o)
        if tr is not None: img = img.transpose(tr)
        img.save(DET / (n[:-4] + ".jpg"), quality=85)
        print(n, "detections", len(out), "median area", int(np.median(out[:, 2])) if len(out) else 0, flush=True)


def tri_rays(O, D):
    """least-squares closest point to rays."""
    A = np.zeros((3, 3)); b = np.zeros(3)
    for o, d in zip(O, D):
        P = np.eye(3) - np.outer(d, d); A += P; b += P @ o
    return np.linalg.solve(A, b)


def refine(cams, X, obs, iters=10):
    """Gauss-Newton on reprojection error. obs: list of (name, uv). returns X, residuals (px), J stacked."""
    for _ in range(iters):
        r, J = [], []
        for n, uv in obs:
            v = cams[n]; p0 = v.project(X[None])[0]
            Jn = np.zeros((2, 3))
            for k in range(3):
                dX = np.zeros(3); dX[k] = 0.01; Jn[:, k] = (v.project((X + dX)[None])[0] - p0) / 0.01
            r.append(p0 - uv); J.append(Jn)
        r = np.concatenate(r); J = np.vstack(J)
        if not (np.isfinite(r).all() and np.isfinite(J).all()):
            return X, np.full(len(obs), np.inf), np.eye(3)
        step = np.linalg.lstsq(J, -r, rcond=None)[0]; X = X + step
        if np.linalg.norm(step) < 1e-4: break
    res = np.array([np.linalg.norm(cams[n].project(X[None])[0] - uv) for n, uv in obs])
    return X, res, J


def cmd_dots(merge=9.0, maxerr=3.0):
    cams = load(); surf = prior_surface()    # the prior is only used for surface normals and a z-difference column
    from scipy.spatial import cKDTree
    BOX = np.array([[-330, -100, 280], [330, 620, 480]], float)      # seat region, chair frame mm
    DUV = {}
    for p in sorted(DET.glob("*.npz")):
        n = p.stem + ".JPG"; z = np.load(p)
        if n in cams.views and len(z["uv"]): DUV[n] = z["uv"]
    names = sorted(DUV); TREE = {n: cKDTree(u) for n, u in DUV.items()}
    print("photos", len(names), "detections", sum(len(u) for u in DUV.values()))
    def gather(X, R):
        """nearest detection to the projection of X in every photo, within R px and unambiguous (2nd > 2R away)"""
        ob = []
        for n, t in TREE.items():
            uv = cams[n].project(X[None])[0]
            if not cams[n].in_image(uv[None])[0]: continue
            d, j = t.query(uv, k=2)
            if d[0] < R and (len(DUV[n]) < 2 or d[1] > 2 * R): ob.append((n, int(j[0]), DUV[n][j[0]]))
        return ob
    def solve(ob):
        X = tri_rays(np.array([cams[n].center for n, _, u in ob]), np.array([cams[n].ray(u[None])[1][0] for n, _, u in ob]))
        return refine(cams, X, [(n, u) for n, _, u in ob])
    # 1) epipolar seeding over photo pairs: detection i in p vs detections in q near the projected ray segment in BOX
    seeds, seen = [], set()
    ctr = np.array([100, 300, 380.0])
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            p, q = names[a], names[b]
            ca, cb = cams[p].center, cams[q].center
            ang = np.degrees(np.arccos(np.clip(np.dot((ca - ctr) / np.linalg.norm(ca - ctr), (cb - ctr) / np.linalg.norm(cb - ctr)), -1, 1)))
            if ang < 8: continue
            o, D = cams[p].ray(DUV[p])
            for i, d in enumerate(D):
                with np.errstate(divide="ignore", invalid="ignore"):
                    t1 = (BOX[0] - o) / d; t2 = (BOX[1] - o) / d
                tn, tf = np.nanmax(np.minimum(t1, t2)), np.nanmin(np.maximum(t1, t2))
                if not (tf > tn > 0): continue
                P = o + np.linspace(tn, tf, 400)[:, None] * d
                uv = cams[q].project(P); uv = uv[np.isfinite(uv).all(1)]
                if len(uv) < 2: continue
                dist, _ = cKDTree(uv).query(DUV[q])
                cand = np.flatnonzero(dist < 4.0)
                for j in cand:
                    key = (p, i, q, int(j))
                    if key in seen: continue
                    seen.add(key)
                    seeds.append((p, i, q, int(j), len(cand) == 1, ang))
    print("pair seeds", len(seeds))
    # 2) each seed -> triangulate -> gather support in all photos -> refine, drop worst while above maxerr
    hyps, done = [], set()
    for p, i, q, j, unique, ang in seeds:
        X, res, J = solve([(p, i, DUV[p][i]), (q, j, DUV[q][j])])
        if res.max() > 4 or not np.all((X > BOX[0]) & (X < BOX[1])): continue
        ob = gather(X, 4.0)
        if len(ob) < 2: continue
        for _ in range(2):
            X, res, J = solve(ob); ob2 = gather(X, maxerr)
            if len(ob2) < 2: break
            ob = ob2
        X, res, J = solve(ob)
        while res.max() > maxerr and len(ob) > 2:
            k = int(np.argmax(res)); ob.pop(k); X, res, J = solve(ob)
        if res.max() > maxerr: continue
        if len(ob) < 3: continue        # 2-photo dots were mostly false epipolar matches (checked 2026-11-20)
        key = frozenset((n, k) for n, k, _ in ob)
        if key in done: continue
        done.add(key)
        hyps.append((len(ob), -np.sqrt((res ** 2).mean()), X, ob, res, J))
    hyps.sort(key=lambda h: (h[0], h[1]), reverse=True)
    used, rows, nconf = set(), [], 0
    for nph, _, X, ob, res, J in hyps:
        keys = {(n, j) for n, j, _ in ob}
        if keys & used: nconf += 1; continue
        if any(np.linalg.norm(X - r_[0]) < 6 for r_ in rows): continue
        used |= keys
        ob = [(n, u) for n, _, u in ob]
        sig = max(np.sqrt((res ** 2).mean()), 0.5)
        cov = np.linalg.inv(J.T @ J) * sig ** 2
        # surface normal from the prior (finite differences)
        e = 1.0; zx = (surf(X[0] + e, X[1]) - surf(X[0] - e, X[1]))[0] / 2 / e; zy = (surf(X[0], X[1] + e) - surf(X[0], X[1] - e))[0] / 2 / e
        nrm = np.array([-zx, -zy, 1.0]); nrm /= np.linalg.norm(nrm)
        C = [cams[n].center for n, _ in ob]; dirs = [(c - X) / np.linalg.norm(c - X) for c in C]
        ang = max(np.degrees(np.arccos(np.clip(np.dot(a, b), -1, 1))) for a in dirs for b in dirs)
        rows.append([X, *X, *np.sqrt(np.diag(cov)), np.sqrt(nrm @ cov @ nrm), len(ob), np.sqrt((res ** 2).mean()), ang,
                     X[2] - surf(X[0], X[1])[0], " ".join(n[4:8] for n, _ in ob)])
    rows = [r[1:] for r in rows]; rows.sort(key=lambda r: (round(r[1] / 20), r[0]))
    out = ROOT / "seat/dots.csv"
    with open(out, "w") as f:
        f.write("id,x_mm,y_mm,z_mm,sx_mm,sy_mm,sz_mm,s_normal_mm,n_photos,rms_px,max_angle_deg,z_minus_cloud_prior_mm,photos\n")
        for k, r in enumerate(rows):
            f.write(f"{k}," + ",".join(f"{x:.2f}" for x in r[:6]) + f",{r[6]:.2f},{r[7]},{r[8]:.2f},{r[9]:.1f},{r[10]:.2f},{r[11]}\n")
    R = np.array([r[:11] for r in rows], float)
    print(f"dots: {len(rows)}  (hypotheses: {len(hyps)}, rejected for sharing a detection: {nconf})")
    if len(R):
        print("n_photos median %d, rms_px median %.2f, s_normal median %.2f mm (p90 %.2f), max_angle median %.0f deg"
              % (np.median(R[:, 7]), np.median(R[:, 8]), np.median(R[:, 6]), np.percentile(R[:, 6], 90), np.median(R[:, 9])))
        print("dot z minus cloud prior surface: median %.2f, rms %.2f mm" % (np.median(R[:, 10]), np.sqrt((R[:, 10] ** 2).mean())))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "detect": cmd_detect(a[1:])
    elif a[0] == "dots":
        kw = {}
        if "--merge" in a: kw["merge"] = float(a[a.index("--merge") + 1])
        if "--maxerr" in a: kw["maxerr"] = float(a[a.index("--maxerr") + 1])
        cmd_dots(**kw)
