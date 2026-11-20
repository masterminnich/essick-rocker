"""USAGE:
  python -I tools/densify.py features [--exclude 1493,1494,...] [--max-feat 40000]
  python -I tools/densify.py match [--k 8]
  python -I tools/densify.py tracks --out work/dense/chair_dense.npy
Denser point cloud ON THE CHAIR using the already-solved cameras (no camera solving, no COLMAP).
features: SIFT (OpenCV) only inside the image region where the chair's 3D bounding box projects; one photo in memory
          at a time; keypoints + descriptors saved per photo in work/dense/feat/.
match:    each photo against its k nearest neighbours in viewing direction (FLANN, ratio test), kept only if the two
          rays meet (two-view reprojection error < 2 px, in front of both cameras, inside the chair box).
tracks:   union-find over pair matches, multi-view triangulation (closest point to rays, then drop observations with
          > 2 px reprojection error), keep points with >= 3 views. Output rows: X Y Z (chair mm), R G B, n_views, rms_px.
Compute audit: features ~1.5 GB peak (SIFT pyramid of one cropped photo), ~8 s/photo on 2 threads; match < 1 GB,
~1-2 s/pair; tracks < 1 GB. Run each stage through tools/safe_run.sh.
"""
import sys, json, argparse, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from rocker.cameras import Cameras
from rocker.ortho import load_raw

BOX = np.array([[-430, -580, -5], [430, 820, 1310]], float)   # chair bounding box, chair frame mm
D = ROOT / "work/dense"; (D / "feat").mkdir(parents=True, exist_ok=True); (D / "pairs").mkdir(exist_ok=True)
CENTER = np.array([0, 100, 500.0])


def box_corners():
    a, b = BOX
    return np.array([[x, y, z] for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])])


def cmd_features(a):
    cams = Cameras.load()
    excl = set(f"IMG_{x}.JPG" for x in a.exclude.split(",") if x)
    cv2.setNumThreads(2)
    sift = cv2.SIFT_create(nfeatures=a.max_feat, contrastThreshold=0.015, edgeThreshold=12)
    for name in cams.names():
        out = D / "feat" / (name[:-4] + ".npz")
        if name in excl or out.exists(): continue
        uv = cams[name].project(box_corners())
        if not np.isfinite(uv).all(): continue
        hull = cv2.convexHull(uv.astype(np.float32)).reshape(-1, 2)
        x0, y0 = np.floor(np.clip(hull.min(0), 0, [4031, 3023])).astype(int); x1, y1 = np.ceil(np.clip(hull.max(0), 0, [4031, 3023])).astype(int)
        if x1 - x0 < 200 or y1 - y0 < 200: continue
        raw = load_raw(cams, name); g = cv2.cvtColor(raw[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        mask = np.zeros(g.shape, np.uint8); cv2.fillConvexPoly(mask, (hull - [x0, y0]).astype(np.int32), 255)
        kp, des = sift.detectAndCompute(g, mask)
        if des is None: continue
        xy = np.array([k.pt for k in kp], np.float32) + [x0, y0]
        col = raw[np.clip(xy[:, 1].round().astype(int), 0, 3023), np.clip(xy[:, 0].round().astype(int), 0, 4031)][:, ::-1]
        np.savez(out, xy=xy, des=des.astype(np.uint8), size=np.array([k.size for k in kp], np.float32), col=col)
        print(name, len(kp), "features, crop", g.shape, flush=True)
        del raw, g, kp, des


def two_view(v1, v2, xy1, xy2):
    """vectorised midpoint triangulation + reprojection error in both views."""
    o1, d1 = v1.ray(xy1); o2, d2 = v2.ray(xy2)
    w = o1 - o2; b = np.sum(d1 * d2, 1); d = d1 @ w; e = d2 @ w
    den = 1 - b * b; den[np.abs(den) < 1e-9] = 1e-9
    t1 = (b * e - d) / den; t2 = (e - b * d) / den
    X = 0.5 * ((o1 + t1[:, None] * d1) + (o2 + t2[:, None] * d2))
    e1 = np.linalg.norm(v1.project(X) - xy1, axis=1); e2 = np.linalg.norm(v2.project(X) - xy2, axis=1)
    ang = np.degrees(np.arccos(np.clip(b, -1, 1)))
    return X, e1, e2, (t1 > 0) & (t2 > 0), ang


def cmd_match(a):
    cams = Cameras.load(); cv2.setNumThreads(2)
    names = sorted(p.stem + ".JPG" for p in (D / "feat").glob("*.npz"))
    C = np.array([cams[n].center for n in names]); dirs = CENTER - C; dist = np.linalg.norm(dirs, axis=1); dirs /= dist[:, None]
    ang = np.degrees(np.arccos(np.clip(dirs @ dirs.T, -1, 1)))
    pairs = set()
    for i in range(len(names)):
        order = np.argsort(ang[i])
        cand = [j for j in order if j != i and 3 < ang[i, j] < 35 and 0.4 < dist[i] / dist[j] < 2.5][:a.k]
        for j in cand: pairs.add((min(i, j), max(i, j)))
    pairs = sorted(pairs); print(len(names), "photos,", len(pairs), "pairs", flush=True)
    cache = {}
    def feat(n):
        if n not in cache:
            if len(cache) > 6: cache.pop(next(iter(cache)))
            z = np.load(D / "feat" / (n[:-4] + ".npz")); cache[n] = (z["xy"].astype(float), z["des"].astype(np.float32))
        return cache[n]
    flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=4), dict(checks=48))
    tot = 0
    for i, j in pairs:
        out = D / "pairs" / f"{names[i][4:8]}_{names[j][4:8]}.npy"
        if out.exists(): continue
        xy1, d1 = feat(names[i]); xy2, d2 = feat(names[j])
        m = flann.knnMatch(d1, d2, k=2)
        q = np.array([[x.queryIdx, x.trainIdx] for x, y in m if x.distance < 0.8 * y.distance], int).reshape(-1, 2)
        if len(q) == 0: np.save(out, q); continue
        X, e1, e2, front, an = two_view(cams[names[i]], cams[names[j]], xy1[q[:, 0]], xy2[q[:, 1]])
        ok = front & (e1 < 2.0) & (e2 < 2.0) & (an > 1.5) & np.all((X > BOX[0]) & (X < BOX[1]), 1)
        # one-to-one
        qq = q[ok]; _, ui = np.unique(qq[:, 1], return_index=True); qq = qq[np.sort(ui)]
        np.save(out, qq); tot += len(qq)
        print(names[i][4:8], names[j][4:8], "ratio", len(q), "geom ok", len(qq), flush=True)
    print("total pair matches this run", tot)


def cmd_tracks(a):
    cams = Cameras.load()
    names = sorted(p.stem + ".JPG" for p in (D / "feat").glob("*.npz"))
    idx = {n[4:8]: k for k, n in enumerate(names)}
    xy = {}; col = {}; off = {}; n_tot = 0
    for k, n in enumerate(names):
        z = np.load(D / "feat" / (n[:-4] + ".npz")); xy[k] = z["xy"].astype(float); col[k] = z["col"]; off[k] = n_tot; n_tot += len(xy[k])
    parent = np.arange(n_tot)
    def find(x):
        r = x
        while parent[r] != r: r = parent[r]
        while parent[x] != r: parent[x], x = r, parent[x]
        return r
    for p in sorted((D / "pairs").glob("*.npy")):
        i, j = idx[p.stem[:4]], idx[p.stem[5:]]
        for q1, q2 in np.load(p):
            r1, r2 = find(off[i] + q1), find(off[j] + q2)
            if r1 != r2: parent[r2] = r1
    roots = np.array([find(x) for x in range(n_tot)])
    order = np.argsort(roots); rs = roots[order]; cuts = np.flatnonzero(np.diff(rs)) + 1
    groups = [g for g in np.split(order, cuts) if len(g) >= 3]
    print("tracks with >=3 obs:", len(groups))
    offs = np.array([off[k] for k in range(len(names))])
    rows = []
    views = [cams[n] for n in names]
    for g in groups:
        ks = np.searchsorted(offs, g, side="right") - 1
        if len(set(ks)) < len(ks): continue        # same photo twice = inconsistent track
        O, Dd, uvs = [], [], []
        for k, gi in zip(ks, g):
            uv = xy[k][gi - offs[k]]; o, d = views[k].ray(uv[None]); O.append(o); Dd.append(d[0]); uvs.append(uv)
        O = np.array(O); Dd = np.array(Dd); uvs = np.array(uvs); keep = np.ones(len(ks), bool)
        for it in range(3):
            A = np.zeros((3, 3)); b = np.zeros(3)
            for o, d in zip(O[keep], Dd[keep]):
                Pm = np.eye(3) - np.outer(d, d); A += Pm; b += Pm @ o
            X = np.linalg.solve(A, b)
            err = np.array([np.linalg.norm(views[k].project(X[None])[0] - uv) for k, uv in zip(ks, uvs)])
            new = err < a.max_err
            if new.sum() < 3: keep = new; break
            if (new == keep).all(): break
            keep = new
        if keep.sum() < 3: continue
        dd = Dd[keep]; ang = np.degrees(np.arccos(np.clip((dd @ dd.T).min(), -1, 1)))
        if ang < 4 or not np.all((X > BOX[0]) & (X < BOX[1])): continue
        c = np.mean([col[k][gi - offs[k]] for k, gi in zip(ks[keep], g[keep])], 0)
        rows.append([*X, *c, keep.sum(), np.sqrt(np.mean(err[keep] ** 2)), ang])
    R = np.array(rows); np.save(a.out, R)
    print("points:", len(R), "| median views", np.median(R[:, 6]), "| median rms px", np.median(R[:, 7]).round(2), "| above table (z>6mm):", int((R[:, 2] > 6).sum()))


ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
f = sub.add_parser("features"); f.add_argument("--exclude", default=""); f.add_argument("--max-feat", type=int, default=40000)
m = sub.add_parser("match"); m.add_argument("--k", type=int, default=8)
t = sub.add_parser("tracks"); t.add_argument("--out", required=True); t.add_argument("--max-err", type=float, default=2.0)
a = ap.parse_args(); {"features": cmd_features, "match": cmd_match, "tracks": cmd_tracks}[a.cmd](a)
