"""USAGE: uv run --no-project --with pycolmap --with numpy --with scipy python -I tools/solve_focal_probe.py \
    --model work/solve/single --out work/solve/focal_probe.json

Evidence test for per-image focal length (focus breathing). For every image, with the 3D points held fixed, refine
(a) pose only and (b) pose + focal (fx=fy scaled together, distortion and principal point fixed) with a Huber loss,
and report RMS reprojection error for both, the relative focal change, and the image's median subject distance
(median depth of its observed points, in model units). If focus breathing matters the focal change should correlate
with subject distance (closer focus -> larger focal) and the error drop should be large for close-ups only.
"""
import argparse, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import rc_geom as G


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m, cams = G.load_model(a.model)
    rows = []
    for im in m.images.values():
        c = cams[im.name]
        X, uv = [], []
        for p in im.points2D:
            if p.has_point3D():
                X.append(m.points3D[p.point3D_id].xyz); uv.append(p.xy)
        X, uv = np.array(X), np.array(uv) * (G.FULL_W / im.camera.width)
        rv0 = Rotation.from_matrix(c.R).as_rotvec()
        p0 = c.p.copy()

        def resid(x, with_f):
            cc = G.Cam(c.name, p0, Rotation.from_rotvec(x[:3]).as_matrix(), x[3:6])
            if with_f: cc.p = p0.copy(); cc.p[:2] *= (1 + x[6])
            return (cc.project(X)[0] - uv).ravel()
        x0 = np.r_[rv0, c.t]
        ra = least_squares(resid, x0, args=(False,), loss="huber", f_scale=2.0)
        rb = least_squares(resid, np.r_[ra.x, 0.0], args=(True,), loss="huber", f_scale=2.0)
        ea = np.linalg.norm(ra.fun.reshape(-1, 2), axis=1); eb = np.linalg.norm(rb.fun.reshape(-1, 2), axis=1)
        # standard error of the focal parameter from the Gauss-Newton normal matrix (inliers)
        J = rb.jac; sig = 1.4826 * np.median(np.abs(rb.fun))
        try:
            cov = np.linalg.inv(J.T @ J) * sig ** 2; sf = float(np.sqrt(cov[6, 6]))
        except np.linalg.LinAlgError:
            sf = None
        depth = np.median(c.to_cam(X)[:, 2])
        rows.append(dict(name=im.name, n=len(X), rms_pose=float(np.sqrt(np.mean(np.minimum(ea, 8) ** 2))),
                         rms_pose_focal=float(np.sqrt(np.mean(np.minimum(eb, 8) ** 2))), dfocal_pct=float(rb.x[6] * 100),
                         dfocal_se_pct=None if sf is None else sf * 100, median_depth=float(depth)))
    rows.sort(key=lambda r: r["median_depth"])
    for r in rows:
        print(f"{r['name'][4:8]} n={r['n']:5d} depth={r['median_depth']:6.3f} rms {r['rms_pose']:.3f} -> {r['rms_pose_focal']:.3f}"
              f"  df={r['dfocal_pct']:+.3f}% (se {r['dfocal_se_pct']:.3f})")
    d = np.array([r["median_depth"] for r in rows]); f = np.array([r["dfocal_pct"] for r in rows])
    print("corr(1/depth, dfocal) =", np.corrcoef(1 / d, f)[0, 1])
    G.save_json(a.out, rows)


if __name__ == "__main__":
    main()
