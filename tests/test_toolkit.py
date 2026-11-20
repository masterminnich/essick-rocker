"""USAGE (from R):
  uv run --no-project --with pycolmap --with numpy --with opencv-python-headless --with pillow --with scipy \
      python -I tests/test_toolkit.py [--model work/sfm/sparse/0] [--n-tracks 3000] [--json work/toolkit/selftest.json]
Self-tests independent of any manual marking:
  (a) project COLMAP's own 3D points with rocker.cameras; compare with their recorded 2D observations
  (b) re-triangulate COLMAP tracks with rocker.triangulate from their observations; compare 3D points
  (c) EXIF orientation round trips (1, 3, 6 + all 8) checked against PIL.ImageOps.exif_transpose
  (d) own distortion model == pycolmap img_from_cam; undistort inverts distort; ray(project(X)) passes X
  (e) sub-pixel refiners (blob, corner, edges) on synthetic images with known truth
Also runs under pytest (functions test_*). Exit code 1 on any failure.
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
from rocker.cameras import Cameras
from rocker.orientation import raw_to_disp, disp_to_raw, to_display_array, disp_size, exif_orientation
from rocker.triangulate import triangulate

_CAMS = {}


def cams(model=None):
    model = model or str(ROOT / "work/sfm/sparse/0")
    if model not in _CAMS:
        _CAMS[model] = Cameras.load(model, metric=None)   # COLMAP units, the frame the tracks live in
    return _CAMS[model]


def test_orientation_against_pil():
    from PIL import Image, ImageOps
    W, H = 40, 30
    rng = np.random.default_rng(0)
    out = {}
    for o in range(1, 9):
        raw = np.zeros((H, W), np.uint8)
        pts = np.c_[rng.integers(0, W, 20), rng.integers(0, H, 20)]
        for i, (x, y) in enumerate(pts):
            raw[y, x] = 10 + i
        im = Image.fromarray(raw); ex = im.getexif(); ex[0x0112] = o
        disp_pil = np.asarray(ImageOps.exif_transpose(Image.open(_save(im, ex))))
        disp_np = to_display_array(raw, o)
        assert disp_pil.shape == disp_np.shape == (disp_size(o, W, H)[1], disp_size(o, W, H)[0]), o
        assert (disp_pil == disp_np).all(), o
        uv = raw_to_disp(pts, o, W, H)
        for i, (u, v) in enumerate(np.round(uv).astype(int)):
            assert disp_pil[v, u] == 10 + i or (raw[pts[i][1], pts[i][0]] != 10 + i), (o, i)
        assert np.allclose(disp_to_raw(uv, o, W, H), pts)
        f = rng.uniform(0, [W - 1, H - 1], (50, 2))       # sub-pixel round trip
        assert np.allclose(disp_to_raw(raw_to_disp(f, o, W, H), o, W, H), f)
        out[o] = "ok"
    return out


def _save(im, ex):
    import io
    b = io.BytesIO(); im.save(b, format="PNG", exif=ex.tobytes()); b.seek(0)
    return b


def test_orientation_real_files():
    """Orientations of the named sample photos, and full-size round trip on their real dimensions."""
    want = {"IMG_1496.JPG": 1, "IMG_1493.JPG": 3, "IMG_1470.JPG": 6}
    got = {}
    for n, o in want.items():
        got[n] = exif_orientation(str(ROOT / "drive" / n))
        assert got[n] == o, (n, got[n])
        corners = np.array([[0, 0], [4031, 0], [0, 3023], [4031, 3023], [1234.25, 987.75]])
        d = raw_to_disp(corners, o)
        dw, dh = disp_size(o)
        assert (d >= 0).all() and (d[:, 0] <= dw - 1).all() and (d[:, 1] <= dh - 1).all()
        assert np.allclose(disp_to_raw(d, o), corners)
    return got


def reproject_colmap(c):
    """Per-observation and per-point (COLMAP's averaging) reprojection errors in model-resolution px."""
    rec = c.rec
    per_obs, per_pt, stored = [], [], []
    for p in rec.points3D.values():
        e = []
        for el in p.track.elements:
            im = rec.images[el.image_id]; v = c[im.name]
            obs_raw = v.scale * im.points2D[el.point2D_idx].xy - 0.5
            e.append(np.linalg.norm(v.project(p.xyz[None])[0] - obs_raw) / v.scale)
        per_obs += e; per_pt.append(np.mean(e)); stored.append(p.error)
    return np.array(per_obs), np.array(per_pt), np.array(stored)


def test_reprojection_matches_colmap(model=None):
    c = cams(model)
    e, pp, stored = reproject_colmap(c)
    colmap_mean = c.rec.compute_mean_reprojection_error()
    out = dict(n_obs=int(len(e)), n_points=int(len(pp)), colmap_reported_mean=float(colmap_mean),
               ours_mean_per_point=float(pp.mean()), max_abs_diff_per_point_vs_colmap=float(np.abs(pp - stored).max()),
               ours_mean_per_obs=float(e.mean()), median_per_obs=float(np.median(e)), p95_per_obs=float(np.percentile(e, 95)),
               max_per_obs=float(e.max()), model_to_raw_scale=float(next(iter(c.views.values())).scale))
    assert abs(pp.mean() - colmap_mean) < 1e-6 and out["max_abs_diff_per_point_vs_colmap"] < 1e-6, out
    return out


def test_retriangulate_tracks(model=None, n=3000):
    """Re-triangulate COLMAP tracks (cameras fixed, plain least squares) and compare with COLMAP's points.
    COLMAP's points come out of a joint bundle adjustment, so exact equality is not expected; the test is that
    our point is at least as good (reprojection cost <= COLMAP's) and the 3D difference is small vs its own sigma."""
    c = cams(model)
    rec = c.rec
    rng = np.random.default_rng(1)
    ids = np.array(list(rec.points3D.keys()))
    ids = rng.choice(ids, min(n, len(ids)), replace=False)
    rel, nsig, dcost, ang = [], [], [], []
    for pid in ids:
        p = rec.points3D[int(pid)]
        obs = []
        for el in p.track.elements:
            im = rec.images[el.image_id]; v = c[im.name]
            obs.append((im.name, v.scale * im.points2D[el.point2D_idx].xy - 0.5))
        r = triangulate(c, obs, sigma_px=1.0, outlier_px=1e9, loss="linear")
        cost_colmap = sum(np.sum((c[nm].project(p.xyz[None])[0] - uv) ** 2) for nm, uv in obs)
        cost_ours = sum(np.sum((c[nm].project(r.X[None])[0] - uv) ** 2) for nm, uv in obs)
        dist = np.linalg.norm(r.X - p.xyz)
        depth = np.median([c[nm].project(p.xyz[None], return_depth=True)[1][0] for nm, _ in obs])
        rel.append(dist / depth); nsig.append(dist / r.sigma_mm); dcost.append((cost_ours - cost_colmap) / max(cost_colmap, 1e-9))
        ang.append(r.ray_angle_deg)
    rel, nsig, dcost, ang = map(np.array, (rel, nsig, dcost, ang))
    good = ang > 5
    out = dict(n_tracks=int(len(ids)), frac_ours_cost_le_colmap=float(np.mean(dcost <= 1e-6)),
               median_rel_err=float(np.median(rel)), p95_rel_err=float(np.percentile(rel, 95)),
               median_dist_in_own_sigmas=float(np.median(nsig)), p95_dist_in_own_sigmas=float(np.percentile(nsig, 95)),
               n_wide_baseline=int(good.sum()), median_rel_err_wide=float(np.median(rel[good])),
               p95_rel_err_wide=float(np.percentile(rel[good], 95)))
    assert out["frac_ours_cost_le_colmap"] > 0.99 and out["p95_dist_in_own_sigmas"] < 1.0, out
    return out


def test_distortion_and_rays(model=None):
    c = cams(model)
    v = c["IMG_1470.JPG"]
    rec_cam = c.rec.cameras[c.rec.images[[i for i, im in c.rec.images.items() if im.name == "IMG_1470.JPG"][0]].camera_id]
    rng = np.random.default_rng(2)
    P = np.c_[rng.uniform(-0.7, 0.7, (500, 2)), np.ones(500)]
    ref = rec_cam.img_from_cam(P)
    from rocker.cameras import _distort
    xd = _distort(v.model, v.params, P[:, :2])
    mine = np.c_[v.fx * xd[:, 0] + v.cx, v.fy * xd[:, 1] + v.cy]
    e_proj = np.abs(mine - ref).max()
    uv = rng.uniform([0, 0], [4031, 3023], (500, 2))
    o, d = v.ray(uv)
    X = o + d * rng.uniform(0.5, 5, (500, 1))
    e_ray = np.abs(v.project(X) - uv).max()
    assert e_proj < 1e-6 and e_ray < 1e-6, (e_proj, e_ray)
    return dict(max_err_vs_pycolmap_px=float(e_proj), max_ray_roundtrip_px=float(e_ray))


def test_refiners_synthetic():
    """Refiners on synthetic images with known sub-pixel truth (8x supersampled, blurred, noise added)."""
    import cv2
    from rocker import refine as rf
    rng = np.random.default_rng(3)
    S = 8
    def render(fn, n=240):
        yy, xx = (np.mgrid[:n * S, :n * S] + 0.5) / S - 0.5          # index-convention coords of fine samples
        hi = fn(xx, yy).astype(np.float32)
        lo = cv2.resize(hi, (n, n), interpolation=cv2.INTER_AREA)
        lo = cv2.GaussianBlur(lo, (0, 0), 0.8) + rng.normal(0, 2.0, lo.shape).astype(np.float32)
        return np.clip(lo, 0, 255).astype(np.uint8)
    out = {}
    cx, cy = 120.37, 119.81                                   # blob: dark ellipse 50x20 px, rotated 20 deg
    t = np.radians(20)
    img = render(lambda x, y: np.where((((x - cx) * np.cos(t) + (y - cy) * np.sin(t)) / 25) ** 2 +
                                       ((-(x - cx) * np.sin(t) + (y - cy) * np.cos(t)) / 10) ** 2 < 1, 60, 150))
    xy, info = rf.blob(img, np.array([126.0, 116.0]), radius=28)
    out["blob_err_px"] = float(np.hypot(xy[0] - cx, xy[1] - cy))
    kx, ky = 118.6, 121.3                                     # corner: bright quadrant x>kx, y>ky
    img = render(lambda x, y: np.where((x > kx) & (y > ky), 210, 50))
    xy, info = rf.corner(img, np.array([116.0, 123.0]), 5)
    out["corner_err_px"] = float(np.hypot(xy[0] - kx, xy[1] - ky))
    # edges: wedge between two lines through (ex, ey) at 10 and 75 degrees
    ex, ey = 121.2, 118.7
    a1, a2 = np.radians(10), np.radians(75)
    img = render(lambda x, y: np.where(((x - ex) * np.sin(a1) - (y - ey) * np.cos(a1) < 0) &
                                       ((x - ex) * np.sin(a2) - (y - ey) * np.cos(a2) > 0), 200, 60))
    d1, d2 = np.array([np.cos(a1), np.sin(a1)]), np.array([np.cos(a2), np.sin(a2)])
    e1 = (np.array([ex, ey]) + 30 * d1 + [0.0, 2.0], np.array([ex, ey]) + 90 * d1)
    e2 = (np.array([ex, ey]) + 30 * d2 + [2.0, 0.0], np.array([ex, ey]) + 90 * d2)
    xy, info = rf.edges(img, e1, e2)
    out["edges_err_px"] = float(np.hypot(xy[0] - ex, xy[1] - ey))
    assert out["blob_err_px"] < 0.3 and out["corner_err_px"] < 0.5 and out["edges_err_px"] < 0.3, out
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=str(ROOT / "work/sfm/sparse/0"))
    ap.add_argument("--n-tracks", type=int, default=3000)
    ap.add_argument("--json", default=str(ROOT / "work/toolkit/selftest.json"))
    a = ap.parse_args()
    results, fail = {}, False
    for name, fn in [("orientation_vs_PIL", test_orientation_against_pil), ("orientation_real_files", test_orientation_real_files),
                     ("distortion_and_rays", lambda: test_distortion_and_rays(a.model)),
                     ("refiners_synthetic", test_refiners_synthetic),
                     ("reprojection_vs_colmap", lambda: test_reprojection_matches_colmap(a.model)),
                     ("retriangulate_tracks", lambda: test_retriangulate_tracks(a.model, a.n_tracks))]:
        try:
            results[name] = {"pass": True, **({"detail": fn()})}
        except AssertionError as e:
            results[name] = {"pass": False, "detail": str(e)}; fail = True
        print(name, json.dumps(results[name], default=str))
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(results, indent=1, default=str))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
