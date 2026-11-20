"""USAGE: tools/py.sh -m 3 -t 5 tools/seat_align.py [--exclude 1507,...] [work/seat/sfm_joint/sparse/0]
Align the joint half-res SfM (dot photos + old photos) to the chair frame through the OLD photos, whose poses are known
in the final model: similarity (Umeyama) on camera centres, then report:
  - centre residuals (mm) and rotation residuals (deg) of the old photos  -> how well the frames agree
  - distance from the joint model's 3D points to the chair cloud (work/dense/chair_dense.npy) -> did the chair move?
Writes the NEW photos' poses into work/seat/poses.json (status "ok", source "joint_sfm"); rocker.seatcams.load() uses them.
Compute audit: loads one small COLMAP model + the 16.7k-point cloud; < 500 MB, seconds."""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, pycolmap
from scipy.spatial import cKDTree
from rocker.cameras import Cameras

args = sys.argv[1:]; EXCL = set()
if "--exclude" in args:
    k = args.index("--exclude"); EXCL = {f"IMG_{x}.JPG" for x in args[k + 1].split(",")}; del args[k:k + 2]
mp = Path(args[0]) if args else ROOT / "work/seat/sfm_joint/sparse/0"
rec = pycolmap.Reconstruction(str(mp)); cams = Cameras.load(); M = cams.metric
J = {}
for im in rec.images.values():
    T = im.cam_from_world().matrix(); J[im.name] = (T[:, :3], T[:, 3])
old = sorted(n for n in J if n in cams.views and n not in EXCL); new = sorted(n for n in J if n not in cams.views)   # --exclude 1507: old photos misregistered in the joint model
A = np.array([-J[n][0].T @ J[n][1] for n in old]); B = np.array([cams[n].center for n in old])
ma, mb = A.mean(0), B.mean(0); a, b = A - ma, B - mb
U, S, Vt = np.linalg.svd(b.T @ a); D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
Rj = U @ D @ Vt; sj = np.trace(np.diag(S) @ D) / (a ** 2).sum(); tj = mb - sj * Rj @ ma
res = B - (sj * (Rj @ A.T).T + tj)
print("old photos used:", len(old), " centre residual mm:", np.round(np.linalg.norm(res, axis=1), 1).tolist())
for n in old:
    Rch = J[n][0] @ Rj.T; dR = Rch @ cams[n].R_chair.T
    print(f"  {n[4:8]} rot diff {np.degrees(np.arccos(np.clip((np.trace(dR) - 1) / 2, -1, 1))):.3f} deg")
P = np.array([p.xyz for p in rec.points3D.values()]); err = np.array([p.error for p in rec.points3D.values()])
Pc = sj * (Rj @ P.T).T + tj
C = np.load(ROOT / "work/dense/chair_dense.npy")[:, :3]
inbox = np.all((Pc > [-430, -580, 5]) & (Pc < [430, 820, 1310]), 1)
d, _ = cKDTree(C).query(Pc[inbox])
print("joint points in chair box:", int(inbox.sum()), " nn distance to chair cloud mm: median %.2f, p25 %.2f, frac<3mm %.2f"
      % (np.median(d), np.percentile(d, 25), (d < 3).mean()))
seat = inbox.copy(); seat[inbox] = (d < 6)
poses = {}   # rewritten from scratch: only the joint-SfM poses of new photos
for n in new:
    Rcj, tcj = J[n]; Rch = Rcj @ Rj.T; tch = sj * tcj - Rch @ tj
    Rcw = Rch @ M.R; tcw = (Rch @ M.t + tch) / M.s
    poses[n] = dict(status="ok", source="joint_sfm", n_inliers=int(rec.images[[i for i, im in rec.images.items() if im.name == n][0]].num_points3D),
                    Rcw=Rcw.tolist(), tcw=tcw.tolist(), center_mm=(-Rch.T @ tch).tolist(),
                    align_centre_rms_mm=float(np.sqrt((res ** 2).sum(1).mean())))
(ROOT / "work/seat/poses.json").write_text(json.dumps(poses, indent=1))
json.dump(dict(model=str(mp), s=sj, R=Rj.tolist(), t=tj.tolist(), old=old, new=new,
               centre_residual_mm=np.linalg.norm(res, axis=1).tolist()), open(ROOT / "work/seat/joint_align.json", "w"), indent=1)
print("scale mm per joint unit", round(sj, 3), " new photos posed:", " ".join(n[4:8] for n in new))
