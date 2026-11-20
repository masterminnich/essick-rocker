"""USAGE: tools/py.sh -t 5 tools/seat_posefix.py [--r 8]
Refine each registered dot photo's pose by resection on the triangulated dots (seat/dots.csv): every dot that projects
into the photo is paired with the nearest detection within --r px (unambiguous: 2nd nearest > 2r); PnP Levenberg-
Marquardt from the current pose (fixed shared intrinsics), Huber-like: two passes, second pass drops pairs > 3 px.
Updates work/seat/poses.json in place (previous pose kept under "Rcw_prev"/"tcw_prev"; "posefix" log appended).
Then rerun `seat_dots.py dots`. Check for gauge drift afterwards: dots vs raw cloud offset must stay ~0 (work/seat/dbg6.py).
Compute: tiny (<200 MB, seconds)."""
import sys, json, csv
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
import numpy as np, cv2
from scipy.spatial import cKDTree
from rocker.seatcams import load
r = float(sys.argv[sys.argv.index("--r") + 1]) if "--r" in sys.argv else 8.0
cams = load(min_inliers=0); M = cams.metric; ref = cams[sorted(n for n in cams.names() if not n.startswith("IMG_159") and not n.startswith("IMG_16"))[0]]
K = np.array([[ref.fx * ref.scale, 0, ref.cx * ref.scale - 0.5], [0, ref.fy * ref.scale, ref.cy * ref.scale - 0.5], [0, 0, 1]])
R_ = list(csv.DictReader(open(ROOT / "seat/dots.csv"))); X = np.array([[float(q[k]) for k in ("x_mm", "y_mm", "z_mm")] for q in R_])
P = json.loads((ROOT / "work/seat/poses.json").read_text())
for n, rec in P.items():
    if rec.get("status") != "ok" or n not in cams.views: continue
    v = cams[n]; dp = ROOT / f"work/seat/det/{n[:-4]}.npz"
    if not dp.exists(): continue
    D = np.load(dp)["uv"]; uv = v.project(X); ok = np.flatnonzero(v.in_image(uv, -5))
    if len(D) < 2 or len(ok) < 8: print(n, "skip: too few"); continue
    # coarse 2D shift first (a pose can be off by tens of px): mode of nearest-detection vectors within 60 px
    d1, j1 = cKDTree(D).query(uv[ok]); vec = (D[j1] - uv[ok])[d1 < 60]
    shift = np.zeros(2)
    if len(vec) >= 8:
        best = max(vec, key=lambda c: (np.linalg.norm(vec - c, axis=1) < 6).sum())
        shift = np.median(vec[np.linalg.norm(vec - best, axis=1) < 6], 0)
    d, j = cKDTree(D).query(uv[ok] + shift, k=2); m = (d[:, 0] < r) & (d[:, 1] > 2 * r)
    Xw = X[ok[m]]
    if len(Xw) < 12: print(n, "skip:", len(Xw), "pairs"); continue
    und = v.undistort_pixels(D[j[m, 0]])
    Rch = v.R_chair; tch = v.to_cam(np.zeros((1, 3)))[0] * M.s
    rvec, tvec = cv2.Rodrigues(Rch)[0], tch.reshape(3, 1).copy()
    e0 = np.linalg.norm(cv2.projectPoints(Xw, rvec, tvec, K, None)[0][:, 0] - und, axis=1)
    keep = np.ones(len(Xw), bool)
    for _ in range(2):
        rvec, tvec = cv2.solvePnPRefineLM(Xw[keep], und[keep], K, None, rvec, tvec)
        e = np.linalg.norm(cv2.projectPoints(Xw, rvec, tvec, K, None)[0][:, 0] - und, axis=1); keep = e < 3.0
    Rn = cv2.Rodrigues(rvec)[0]; tn = tvec[:, 0]
    c_old, c_new = -Rch.T @ tch, -Rn.T @ tn
    rec.setdefault("Rcw_prev", rec["Rcw"]); rec.setdefault("tcw_prev", rec["tcw"])
    rec["Rcw"] = (Rn @ M.R).tolist(); rec["tcw"] = ((Rn @ M.t + tn) / M.s).tolist(); rec["center_mm"] = c_new.tolist()
    log = dict(shift_px=np.round(shift, 1).tolist(), pairs=int(len(Xw)), kept=int(keep.sum()), rms_before=float(np.sqrt((e0 ** 2).mean())), rms_after=float(np.sqrt((e[keep] ** 2).mean())),
               moved_mm=float(np.linalg.norm(c_new - c_old)))
    rec.setdefault("posefix", []).append(log)
    print(n, log)
(ROOT / "work/seat/poses.json").write_text(json.dumps(P, indent=1))
