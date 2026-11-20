"""USAGE:
  tools/py.sh -m 4 -t 15 tools/seat_register.py bank                 # build the 2D-3D descriptor bank (once)
  tools/py.sh -m 4 -t 20 tools/seat_register.py register IMG_1595 ... # register new photos (pose per photo)
Register NEW photos into the solved chair model WITHOUT COLMAP: chair points only.

bank:     for each of the 70 photos with features in work/dense/feat, project the chair cloud
          (work/dense/chair_dense.npy, >=3 views, rms<1.5 px) and attach each point to the nearest SIFT feature within
          1.0 px. Saved: work/seat/bank.npz (descriptor, 3D point, source photo). Occlusion is not modelled; RANSAC copes.
register: SIFT on the whole new photo (CLAHE, 1400 px tiles, as densify.py), ratio-test match to the bank (FLANN),
          undistort with the model's shared intrinsics (same phone, same 26 mm lens, no zoom), PnP RANSAC (4 px) then
          Levenberg-Marquardt on the inliers. Writes/updates work/seat/poses.json (COLMAP-frame Rcw, tcw so the pose can
          be used by rocker.cameras.View) with inlier count, rms and median reprojection error.
          Load registered views with rocker.seatcams.load().
Compute audit: bank ~ 70 x 6 MB npz read one at a time, peak < 1 GB, ~1-2 min. register: one photo decoded at a time
(36 MB), SIFT on tiles ~0.6 GB, FLANN vs bank (~100-200k x 128 float32 <= 100 MB), 2 threads, ~30-60 s/photo.
"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from rocker.cameras import Cameras
from PIL import Image

D = ROOT / "work/seat"; D.mkdir(parents=True, exist_ok=True)
BANK = D / "bank.npz"; POSES = D / "poses.json"


def cmd_bank():
    from scipy.spatial import cKDTree
    cams = Cameras.load()
    C = np.load(ROOT / "work/dense/chair_dense.npy")
    C = C[(C[:, 6] >= 3) & (C[:, 7] < 1.5)]; X = C[:, :3]
    print("cloud points used", len(X))
    des_l, X_l, src_l = [], [], []
    for k, p in enumerate(sorted((ROOT / "work/dense/feat").glob("*.npz"))):
        name = p.stem + ".JPG"; z = np.load(p); xy = z["xy"].astype(float)
        uv = cams[name].project(X); ok = cams[name].in_image(uv)
        tree = cKDTree(xy); d, j = tree.query(uv[ok], distance_upper_bound=1.0)
        hit = np.isfinite(d); pid = np.flatnonzero(ok)[hit]; fid = j[hit]
        # one feature -> one point (keep the closest)
        order = np.argsort(d[hit]); _, first = np.unique(fid[order], return_index=True); sel = order[first]
        des_l.append(z["des"][fid[sel]]); X_l.append(X[pid[sel]]); src_l.append(np.full(len(sel), k, np.int16))
        print(name, len(xy), "features,", len(sel), "lifted", flush=True)
    np.savez(BANK, des=np.vstack(des_l).astype(np.uint8), X=np.vstack(X_l).astype(np.float32), src=np.concatenate(src_l))
    print("bank", sum(len(s) for s in src_l))


def sift_photo(path):
    im = Image.open(path).convert("L"); g = np.asarray(im); del im
    g = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(g)
    sift = cv2.SIFT_create(nfeatures=12000, contrastThreshold=0.006, edgeThreshold=12)
    T, OV = 1400, 96; xs, ds = [], []
    for ty in range(0, g.shape[0], T):
        for tx in range(0, g.shape[1], T):
            ya, yb = max(0, ty - OV), min(g.shape[0], ty + T + OV); xa, xb = max(0, tx - OV), min(g.shape[1], tx + T + OV)
            m = np.zeros((yb - ya, xb - xa), np.uint8); m[ty - ya:ty - ya + T, tx - xa:tx - xa + T] = 255
            kp, des = sift.detectAndCompute(np.ascontiguousarray(g[ya:yb, xa:xb]), m)
            if des is None: continue
            xs.append(np.array([k.pt for k in kp], np.float32) + [xa, ya]); ds.append(des)
    return np.vstack(xs).astype(float), np.vstack(ds).astype(np.float32)


def cmd_register(names):
    cv2.setNumThreads(2)
    cams = Cameras.load(); ref = cams[cams.names()[0]]; M = cams.metric
    b = np.load(BANK); keep = np.ones(len(b["src"]), bool)
    feats = sorted(q.stem + ".JPG" for q in (ROOT / "work/dense/feat").glob("*.npz"))
    for n in names:   # leave-one-out: never match a photo against its own bank entries
        nn = n if n.endswith(".JPG") else (n if n.startswith("IMG_") else "IMG_" + n) + ".JPG"
        if nn in feats: keep &= b["src"] != feats.index(nn)
    bdes = b["des"][keep].astype(np.float32); bX = b["X"][keep].astype(float)
    flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=4), dict(checks=64))
    flann.add([bdes]); flann.train()
    K = np.array([[ref.fx * ref.scale, 0, ref.cx * ref.scale - 0.5], [0, ref.fy * ref.scale, ref.cy * ref.scale - 0.5], [0, 0, 1]])
    poses = json.loads(POSES.read_text()) if POSES.exists() else {}
    for n in names:
        name = n if n.endswith(".JPG") else (n if n.startswith("IMG_") else "IMG_" + n) + ".JPG"
        xy, des = sift_photo(cams.drive / name)
        mm = flann.knnMatch(des, k=2)
        good = [(a.queryIdx, a.trainIdx) for a, c in mm if a.distance < 0.8 * c.distance]
        q = np.array([g[0] for g in good]); t = np.array([g[1] for g in good])
        und = ref.undistort_pixels(xy[q]); Xw = bX[t]
        ok, rvec, tvec, inl = cv2.solvePnPRansac(Xw, und, K, None, iterationsCount=20000, reprojectionError=4.0,
                                                 confidence=0.9999, flags=cv2.SOLVEPNP_SQPNP)
        rec = {"n_features": len(xy), "n_matches": len(good)}
        if not ok or inl is None or len(inl) < 30:
            rec.update(status="FAILED", n_inliers=0 if inl is None else len(inl)); print(name, rec, flush=True)
            poses[name] = rec; continue
        inl = inl[:, 0]
        for _ in range(2):    # LM refine, then re-collect inliers at 3 px and refine again
            rvec, tvec = cv2.solvePnPRefineLM(Xw[inl], und[inl], K, None, rvec, tvec)
            pr = cv2.projectPoints(Xw, rvec, tvec, K, None)[0][:, 0]; e = np.linalg.norm(pr - und, axis=1)
            inl = np.flatnonzero(e < 3.0)
        Rch = cv2.Rodrigues(rvec)[0]; tch = tvec[:, 0]
        # chair-frame pose (mm) -> COLMAP-frame pose:  x_cam_colmap = (Rch R) Xc + (Rch t + tch)/s
        Rcw = Rch @ M.R; tcw = (Rch @ M.t + tch) / M.s
        ei = e[inl]
        rec.update(status="ok", n_inliers=int(len(inl)), rms_px=float(np.sqrt((ei ** 2).mean())), med_px=float(np.median(ei)),
                   Rcw=Rcw.tolist(), tcw=tcw.tolist(), center_mm=(-Rch.T @ tch).tolist(),
                   inlier_spread_mm=np.ptp(Xw[inl], 0).round(0).tolist())
        poses[name] = rec
        print(name, {k: v for k, v in rec.items() if k not in ("Rcw", "tcw")}, flush=True)
        POSES.write_text(json.dumps(poses, indent=1))
        del xy, des, mm


if __name__ == "__main__":
    if sys.argv[1] == "bank": cmd_bank()
    elif sys.argv[1] == "register": cmd_register(sys.argv[2:])
